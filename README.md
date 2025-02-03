# Bluesky Firehose Archiver

A Python library for collecting and archiving posts from the Bluesky social network using the [Jetstream API](https://github.com/bluesky-social/jetstream). This tool connects to Bluesky's firehose and saves posts in an organized file structure.

## Features

- Connects to Bluesky's Jetstream websocket API
- Three archiving modes:
  - Posts only (default)
  - All records (posts, likes, follows, etc.)
  - Non-posts only (everything except posts)
- Archives data in JSONL format, organized by date and hour
- Optional real-time post text streaming to stdout
- Automatic reconnection on connection loss
- Efficient batch processing and disk operations
- Debug mode for detailed logging
- Optional handle resolution (disabled by default)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/bluesky-firehose-archiver.git
```

2. Navigate to the project directory:
```bash
cd bluesky-firehose-archiver
```

3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. For development/testing:
```bash
pip install -r requirements-dev.txt
```

## Usage

### As a Command Line Tool

Basic usage:
```bash
python src/main.py
```

Available command line options:
```bash
python src/main.py [options]

Options:
  --username         Bluesky username (optional)
  --password         Bluesky password (optional)
  --debug           Enable debug output
  --stream          Stream post text to stdout in real-time
  --measure-rate    Track and display posts per minute rate
  --get-handles     Resolve handles while archiving (not recommended)
  --cursor          Unix microseconds timestamp to start playback from
  --archive-all     Archive all records in their original format
  --archive-non-posts Archive everything except posts
```

### Archiving Modes

The archiver supports three distinct modes of operation:

1. **Posts Only** (default):
```bash
python src/main.py
```
- Archives only posts (`app.bsky.feed.post` records)
- Saves to `data/` directory
- Files named `posts_YYYYMMDD_HH.jsonl`

2. **All Records**:
```bash
python src/main.py --archive-all
```
- Archives all record types (posts, likes, follows, etc.)
- Saves to `data_everything/` directory
- Files named `records_YYYYMMDD_HH.jsonl`
- Preserves complete record structure

3. **Non-Posts Only**:
```bash
python src/main.py --archive-non-posts
```
- Archives everything except posts
- Saves to `data_non_posts/` directory
- Files named `records_YYYYMMDD_HH.jsonl`
- Useful for collecting only interactions and profile updates

Note: The `--archive-all` and `--archive-non-posts` modes cannot be used simultaneously.

### As a Library

You can use the archiver in two ways:

1. Archive posts to disk:
```python
from archiver import BlueskyArchiver
import asyncio

async def main():
    archiver = BlueskyArchiver(debug=True, stream=True)
    await archiver.archive_posts()  # This will save posts to disk

asyncio.run(main())
```

2. Stream posts in your code:
```python
from archiver import BlueskyArchiver
import asyncio

async def main():
    archiver = BlueskyArchiver()
    
    async for post in archiver.stream_posts():
        # Process each post as it arrives
        print(f"New post from @{post['handle']}: {post['record']['text']}")
        
        # Example: Filter posts containing specific text
        if "python" in post['record']['text'].lower():
            # Do something with Python-related posts
            process_python_post(post)

asyncio.run(main())
```

3. **Run Archiving and Streaming Concurrently**:
```python
from archiver import BlueskyArchiver
import asyncio

async def main():
    archiver = BlueskyArchiver(debug=True, stream=True, measure_rate=True)
    
    async for post in archiver.run_stream():
        # Process each post as it arrives
        print(f"New post from @{post['handle']}: {post['record']['text']}")

        # Example: Additional processing
        # process_post(post)

asyncio.run(main())
```

### Example Use Cases:
- Real-time content analysis
- Custom filtering and processing
- Integration with other services
- Building real-time dashboards
- Research and data collection

## Data Storage

Records are saved in JSONL (JSON Lines) format, organized by date and hour in different directories based on the archiving mode:

```
data/                      # Posts only mode (default)
  └── YYYY-MM/
      └── DD/
          └── posts_YYYYMMDD_HH.jsonl

data_everything/          # Archive all mode
  └── YYYY-MM/
      └── DD/
          └── records_YYYYMMDD_HH.jsonl

data_non_posts/          # Non-posts mode
  └── YYYY-MM/
      └── DD/
          └── records_YYYYMMDD_HH.jsonl
```

### Record Format

1. **Posts Only Mode** (default):
```json
{
    "handle": "user.bsky.social",
    "record": {
        "text": "Post content",
        "createdAt": "2024-03-15T01:23:45.678Z",
        ...
    },
    "rkey": "unique-record-key",
    "did": "did:plc:abcd...",
    "time_us": 1234567890
}
```

2. **Archive All & Non-Posts Modes**:
```json
{
    "did": "did:plc:abcd...",
    "time_us": 1234567890,
    "kind": "commit",
    "commit": {
        "rev": "...",
        "operation": "create",
        "collection": "app.bsky.feed.like",  // or other collection types
        "rkey": "...",
        "record": { ... }
    }
}
```

## Project Structure

```
├── src/
│   ├── main.py           # Entry point and CLI interface
│   └── archiver.py       # Core archiving logic
├── data/                 # Archived posts storage
├── requirements.txt      # Project dependencies
└── README.md            # This file
```

## License

MIT License 

### Playback Feature

The archiver supports playback from a specific point in time using the Jetstream cursor functionality. To use this feature:

```bash
# Start archiving from a specific timestamp (Unix microseconds)
python src/main.py --cursor 1725911162329308
```

Notes about playback:
- The cursor should be a Unix timestamp in microseconds
- Playback will start from the specified time and continue to real-time
- You can find the timestamp in the saved posts' `time_us` field

### Complete Record Archiving

By default, the archiver only saves post records. To archive all record types (posts, likes, follows, etc.) in their original format:

```bash
python src/main.py --archive-all
```

This will:
- Save all records without filtering by collection
- Preserve the original JSON structure from the firehose
- Store files in the `data_everything` directory
- Include all record types (posts, likes, follows, profiles, etc.)

The records are saved in JSONL format with the original structure:
```json
{
    "did": "did:plc:abcd...",
    "time_us": 1234567890,
    "kind": "commit",
    "commit": {
        "rev": "...",
        "operation": "create",
        "collection": "app.bsky.feed.post",
        "rkey": "...",
        "record": { ... }
    }
}
```
