"""
Management command to comprehensively tag all 4,007 OSRS items.
"""

import asyncio
from django.core.management.base import BaseCommand
from services.comprehensive_item_tagger import ComprehensiveItemTagger


class Command(BaseCommand):
    help = 'Comprehensively tag all OSRS items with intelligent categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of items to process in each batch'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting comprehensive item tagging...'))
        
        # Run async tagging process
        results = asyncio.run(self.run_tagging())
        
        self.stdout.write(self.style.SUCCESS('\n=== TAGGING RESULTS ==='))
        self.stdout.write(f"Total items: {results['total_items']}")
        self.stdout.write(f"Total tag mappings: {results['total_mappings']}")
        self.stdout.write(f"Total categories: {results['total_categories']}")
        
        self.stdout.write('\n=== TAG DISTRIBUTION ===')
        for tag, count in sorted(results['tag_counts'].items()):
            self.stdout.write(f"{tag}: {count} items")
        
        self.stdout.write(self.style.SUCCESS('\nComprehensive tagging completed!'))

    async def run_tagging(self):
        """Run the async tagging process."""
        tagger = ComprehensiveItemTagger()
        return await tagger.tag_all_items()