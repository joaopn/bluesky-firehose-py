import argparse
import asyncio
import signal
import sys
from archiver import BlueskyArchiver

async def run_archiver(args):
    """Run the archiver with the given arguments."""
    archiver = BlueskyArchiver(
        username=args.username, 
        password=args.password, 
        debug=args.debug,
        stream=args.stream
    )
    
    def handle_shutdown(sig, frame):
        """Handle shutdown signals."""
        print("\nShutting down gracefully...")
        archiver.stop()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        await archiver.archive_posts()
    finally:
        archiver.stop()

def main():
    """Main function to run the archiver with signal handling."""
    parser = argparse.ArgumentParser(description='Archive posts from Bluesky firehose')
    parser.add_argument('--username', help='Bluesky username')
    parser.add_argument('--password', help='Bluesky password')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--stream', action='store_true', help='Stream post text to stdout')
    
    args = parser.parse_args()
    
    if sys.platform == 'win32':
        # Windows specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(run_archiver(args))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main() 