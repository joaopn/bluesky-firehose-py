# Bluesky Firehose Archiver

A Python library for collecting and archiving posts from the Bluesky social network using the [Jetstream API](https://github.com/bluesky-social/jetstream). This tool connects to Bluesky's firehose and saves posts in an organized file structure.

## Features

- Connects to Bluesky's Jetstream websocket API
- Archives posts in JSONL format, organized by date and hour
- Optional real-time post text streaming to stdout
- Automatic reconnection on connection loss
- Efficient batch processing and disk operations
- Debug mode for detailed logging

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
  --username    Bluesky username (optional)
  --password    Bluesky password (optional)
  --debug       Enable debug output
  --stream      Stream post text to stdout in real-time
```

Note: Authentication (username/password) is currently implemented but not required for basic operation. Future versions will use authentication to fetch additional user and post metadata.

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

Example use cases:
- Real-time content analysis
- Custom filtering and processing
- Integration with other services
- Building real-time dashboards
- Research and data collection

## Data Storage

Posts are automatically saved in JSONL (JSON Lines) format, organized by date and hour:

```
data/
  └── YYYY-MM/
      └── DD/
          └── posts_YYYYMMDD_HH.jsonl
```

Each JSONL file contains one post per line in JSON format with the following structure:
```json
{
    "handle": "user.bsky.social",
    "timestamp": "2024-03-15T01:23:45.678Z",
    "record": {
        "text": "Post content",
        "createdAt": "2024-03-15T01:23:45.678Z",
        ...
    },
    "rkey": "unique-record-key",
    ...
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