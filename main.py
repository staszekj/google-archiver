"""Google Photos Archiver - Main Entry Point."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

import config


class PhotosArchiver:
    """Manages archiving old photos from Google Photos."""
    
    def __init__(self):
        self.cutoff_date = datetime.now() - timedelta(days=365 * config.CUTOFF_YEARS)
        self.service = None
        self.stats = {
            'total_photos': 0,
            'eligible_photos': 0,
            'in_albums': 0,
            'to_archive': 0,
            'total_size_mb': 0
        }
    
    def authenticate(self):
        """Authenticate with Google Photos API."""
        print("🔐 Authenticating with Google Photos...")
        # TODO: Implement OAuth2 authentication
        print("⚠️  Authentication not implemented yet")
        print("    Need credentials.json from Google Cloud Console")
        return False
    
    def get_all_photos(self) -> List[Dict]:
        """Fetch all photos from Google Photos."""
        print(f"📸 Fetching photos older than {self.cutoff_date.strftime('%Y-%m-%d')}...")
        # TODO: Implement Google Photos API calls
        return []
    
    def get_albums(self) -> Dict:
        """Fetch all albums and their photo IDs."""
        print("📚 Fetching albums...")
        # TODO: Implement albums listing
        return {}
    
    def filter_photos_not_in_albums(self, photos: List[Dict], albums: Dict) -> List[Dict]:
        """Filter photos that are NOT in any album."""
        print("🔍 Filtering photos not in albums...")
        # TODO: Implement filtering logic
        return []
    
    def dry_run_report(self, photos: List[Dict]):
        """Generate dry-run report of what would be archived."""
        print("\n" + "="*60)
        print("📊 DRY RUN REPORT")
        print("="*60)
        print(f"Cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}")
        print(f"Archive path: {config.ARCHIVE_PATH}")
        print(f"\nTotal photos checked: {self.stats['total_photos']}")
        print(f"Photos older than {config.CUTOFF_YEARS} years: {self.stats['eligible_photos']}")
        print(f"Photos in albums (skipped): {self.stats['in_albums']}")
        print(f"Photos to archive: {self.stats['to_archive']}")
        print(f"Total size: {self.stats['total_size_mb']:.2f} MB")
        print("="*60)
        
        if photos:
            print(f"\nFirst 10 photos that would be archived:")
            for i, photo in enumerate(photos[:10], 1):
                print(f"  {i}. {photo.get('filename', 'Unknown')} - {photo.get('date', 'N/A')}")
    
    def run(self):
        """Main execution flow."""
        print("🚀 Google Photos Archiver")
        print(f"Mode: {'DRY RUN' if config.DRY_RUN else 'LIVE'}")
        print(f"Cutoff: {config.CUTOFF_YEARS} years")
        print()
        
        # Step 1: Authenticate
        if not self.authenticate():
            print("❌ Authentication failed. Please set up credentials.json")
            return 1
        
        # Step 2: Fetch photos
        all_photos = self.get_all_photos()
        self.stats['total_photos'] = len(all_photos)
        
        # Step 3: Fetch albums
        albums = self.get_albums()
        
        # Step 4: Filter photos
        photos_to_archive = self.filter_photos_not_in_albums(all_photos, albums)
        self.stats['to_archive'] = len(photos_to_archive)
        
        # Step 5: Dry run report
        if config.DRY_RUN:
            self.dry_run_report(photos_to_archive)
            print("\n✅ Dry run complete. No changes made.")
        else:
            print("⚠️  LIVE mode not implemented yet")
        
        return 0


def main():
    """Entry point."""
    archiver = PhotosArchiver()
    return archiver.run()


if __name__ == '__main__':
    sys.exit(main())
