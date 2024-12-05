import websockets
import asyncio
import json
from datetime import datetime
import os
from atproto import Client, models
from typing import Dict, Optional, List
from collections import deque
from asyncio import Queue
import logging
import aiofiles
import sys

class BlueskyArchiver:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, debug: bool = False, stream: bool = False):
        """Initialize the Bluesky Archiver.
        
        Args:
            username: Bluesky username (optional)
            password: Bluesky password (optional)
            debug: Enable debug output (default: False)
            stream: Stream post text to stdout (default: False)
        """
        # Suppress HTTP request logging
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        self.debug = debug
        self.client = Client()
        if username and password:
            self.client.login(username, password)
        
        self.uri = "wss://jetstream2.us-east.bsky.network/subscribe"
        self.handle_cache: Dict[str, str] = {}  # Cache DID -> handle mapping
        self.running = True
        
        # Add two queues - one for incoming posts and one for disk operations
        self.post_queue = Queue()
        self.disk_queue = Queue()
        self.save_task = None
        self.disk_task = None
        
        if self.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        else:
            logging.basicConfig(
                level=logging.WARNING,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        
        self.stream = stream
        
    async def get_handle(self, did: str) -> Optional[str]:
        """Get handle for a DID using repo.describe_repo.
        
        Args:
            did: The DID to look up
            
        Returns:
            Handle string or None if not found
        """
        if did in self.handle_cache:
            return self.handle_cache[did]
            
        try:
            response = self.client.com.atproto.repo.describe_repo({'repo': did})
            handle = response.handle
            self.handle_cache[did] = handle
            return handle
        except Exception as e:
            logging.error(f"🔴 Error getting handle for {did}")
            return None

    async def save_posts_async(self, posts: List[dict], filename: Optional[str] = None):
        """Asynchronously save posts to JSONL files, organizing by hour.
        
        Args:
            posts: List of post records to save
            filename: Optional custom filename, otherwise organizes by hour
        """
        if filename:
            # If filename is provided, save all posts to that file
            async with aiofiles.open(filename, 'a', encoding='utf-8') as f:
                for post in posts:
                    await f.write(json.dumps(post, ensure_ascii=False) + '\n')
            return
            
        # Group posts by hour
        posts_by_hour = {}
        for post in posts:
            # Parse the timestamp from the post
            post_time = datetime.fromisoformat(post['timestamp'])
            
            # Create the hour key and filename
            date_dir = post_time.strftime('%Y-%m/%d')
            hour_filename = post_time.strftime('posts_%Y%m%d_%H.jsonl')
            full_path = f"data/{date_dir}/{hour_filename}"
            
            if full_path not in posts_by_hour:
                posts_by_hour[full_path] = []
            posts_by_hour[full_path].append(post)
        
        # Save posts to their respective hour files
        for full_path, hour_posts in posts_by_hour.items():
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Append posts to the hour's file
            async with aiofiles.open(full_path, 'a', encoding='utf-8') as f:
                for post in hour_posts:
                    await f.write(json.dumps(post, ensure_ascii=False) + '\n')

    async def disk_worker(self):
        """Background task to handle disk operations."""
        while self.running:
            try:
                posts, filename = await asyncio.wait_for(self.disk_queue.get(), timeout=1.0)
                await self.save_posts_async(posts, filename)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"🔴 Error in disk worker: {e}")

    async def save_worker(self):
        """Background task to batch posts and queue them for saving."""
        posts_batch = []
        while self.running:
            try:
                # Wait for posts with a timeout
                post = await asyncio.wait_for(self.post_queue.get(), timeout=1.0)
                posts_batch.append(post)
                
                # Check if we have more posts waiting
                while len(posts_batch) < 100 and not self.post_queue.empty():
                    posts_batch.append(await self.post_queue.get())
                    
                # Queue the batch for disk operations without waiting
                if posts_batch:
                    await self.disk_queue.put((posts_batch.copy(), None))
                    posts_batch = []
                
            except asyncio.TimeoutError:
                # If we have posts in the batch when timeout occurs, queue them
                if posts_batch:
                    await self.disk_queue.put((posts_batch.copy(), None))
                    posts_batch = []
            except Exception as e:
                logging.error(f"🔴 Error in save worker: {e}")
                
        # Final save of any remaining posts
        if posts_batch:
            await self.disk_queue.put((posts_batch.copy(), None))

    async def archive_posts(self):
        """Archive posts from the Bluesky firehose with automatic reconnection."""
        # Start both worker tasks
        self.save_task = asyncio.create_task(self.save_worker())
        self.disk_task = asyncio.create_task(self.disk_worker())
        
        while self.running:
            try:
                params = {
                    "wantedCollections": ["app.bsky.feed.post"]
                }
                url = f"{self.uri}?{'&'.join(f'wantedCollections={c}' for c in params['wantedCollections'])}"
                
                async with websockets.connect(url) as websocket:
                    if self.debug:
                        logging.debug("🟢 Connected to firehose")
                    while self.running:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            
                            if not self.running:
                                break
                            
                            if data["kind"] == "commit":
                                commit = data["commit"]
                                if commit["operation"] == "create":
                                    handle = await self.get_handle(data['did'])
                                    
                                    post_record = {
                                        'handle': handle,
                                        'timestamp': datetime.now().isoformat(),
                                        'record': commit['record'],
                                        "rkey": commit['rkey']
                                    }
                                    
                                    for key, value in data.items():
                                        if key != "kind" and key != "commit":
                                            post_record[key] = value
                                    
                                    # Stream post text if enabled
                                    if self.stream and 'text' in commit['record']:
                                        sys.stdout.write(f"🖊️: {commit['record']['text']}\n")
                                        sys.stdout.flush()
                                    
                                    await self.post_queue.put(post_record)
                                    if self.debug:
                                        logging.debug(f"🟢 Archived post from {handle or data['did']}")
                                    
                        except websockets.exceptions.ConnectionClosed:
                            logging.debug("🔴 Connection closed, attempting to reconnect...")
                            break
                            
            except Exception as e:
                if not self.running:
                    break
                logging.error(f"🔴 Error in connection: {e}")
                print("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
        
        # Wait for tasks to complete when stopping
        if self.save_task and self.disk_task:
            try:
                await asyncio.wait_for(asyncio.gather(self.save_task, self.disk_task), timeout=5.0)
            except asyncio.TimeoutError:
                logging.warning("🔴 Timeout waiting for tasks to complete")

    def stop(self):
        """Stop the archiver gracefully."""
        self.running = False

    async def stream_posts(self):
        """Stream posts as they arrive from the firehose.
        
        Yields:
            dict: Post record containing handle, timestamp, record data and metadata
        """
        self.running = True
        
        while self.running:
            try:
                params = {
                    "wantedCollections": ["app.bsky.feed.post"]
                }
                url = f"{self.uri}?{'&'.join(f'wantedCollections={c}' for c in params['wantedCollections'])}"
                
                async with websockets.connect(url) as websocket:
                    if self.debug:
                        logging.debug("🟢 Connected to firehose")
                    while self.running:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            
                            if not self.running:
                                break
                            
                            if data["kind"] == "commit":
                                commit = data["commit"]
                                if commit["operation"] == "create":
                                    handle = await self.get_handle(data['did'])
                                    
                                    post_record = {
                                        'handle': handle,
                                        'timestamp': datetime.now().isoformat(),
                                        'record': commit['record'],
                                        "rkey": commit['rkey']
                                    }
                                    
                                    for key, value in data.items():
                                        if key != "kind" and key != "commit":
                                            post_record[key] = value
                                    
                                    yield post_record
                                    
                        except websockets.exceptions.ConnectionClosed:
                            logging.debug("🔴 Connection closed, attempting to reconnect...")
                            break
                            
            except Exception as e:
                if not self.running:
                    break
                logging.error(f"🔴 Error in connection: {e}")
                await asyncio.sleep(5)
