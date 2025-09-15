"""
Management command to bootstrap historical data for top trading items.

Usage:
    python manage.py bootstrap_historical_data [--items 50] [--force]
"""

import asyncio
from django.core.management.base import BaseCommand, CommandError
from services.historical_data_service import bootstrap_historical_data


class Command(BaseCommand):
    help = 'Bootstrap historical data for top trading items'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=int,
            default=50,
            help='Number of top items to process (default: 50)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh existing data'
        )
    
    def handle(self, *args, **options):
        items_count = options['items']
        force_refresh = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🚀 Bootstrapping historical data for top {items_count} items'
            )
        )
        
        try:
            stats = asyncio.run(bootstrap_historical_data(items_count, force_refresh))
            
            self.stdout.write(self.style.SUCCESS('\n✅ Historical data bootstrap completed!'))
            self.stdout.write('📊 Statistics:')
            for key, value in stats.items():
                self.stdout.write(f'  • {key}: {value}')
                
        except Exception as e:
            raise CommandError(f'Failed to bootstrap historical data: {e}')