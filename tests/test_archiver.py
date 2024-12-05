import asyncio
import os
import sys

# Add the parent directory to Python path to find the src module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.archiver import BlueskyArchiver

async def test_stream_posts():
    """Test that stream_posts yields valid post records."""
    print("\nTesting stream_posts functionality...")
    archiver = BlueskyArchiver()
    posts_received = 0
    required_fields = {'handle', 'timestamp', 'record', 'rkey'}
    
    try:
        async for post in archiver.stream_posts():
            # Verify post structure
            if not isinstance(post, dict):
                raise AssertionError("Post should be a dictionary")
            
            # Check required fields
            missing_fields = required_fields - post.keys()
            if missing_fields:
                raise AssertionError(
                    f"Post missing required fields: {missing_fields}"
                )
            
            # Verify record structure
            if 'text' not in post['record']:
                raise AssertionError("Post record should contain text")
            if 'createdAt' not in post['record']:
                raise AssertionError("Post record should contain createdAt")
            
            posts_received += 1
            print(f"✓ Received post {posts_received}: {post['record']['text'][:100]}...")
            
            if posts_received >= 3:  # Test with first 3 posts
                archiver.stop()
                break
                
    except Exception as e:
        archiver.stop()
        raise e
    
    if posts_received == 0:
        raise AssertionError("Should receive at least one post")
    
    print(f"✓ Successfully received and validated {posts_received} posts")
    return True

def run_tests():
    """Run all tests."""
    try:
        asyncio.run(test_stream_posts())
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        raise e

if __name__ == "__main__":
    run_tests()