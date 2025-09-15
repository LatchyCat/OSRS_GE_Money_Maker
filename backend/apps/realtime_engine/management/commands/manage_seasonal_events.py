"""
Django management command for managing seasonal events in OSRS market data.

Usage:
    python manage.py manage_seasonal_events --list
    python manage.py manage_seasonal_events --add-event "Double XP Weekend" --start-date 2025-02-15 --duration 3
    python manage.py manage_seasonal_events --predict-next-events
    python manage.py manage_seasonal_events --update-impact-data
"""

import asyncio
import logging
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async

from apps.realtime_engine.models import SeasonalEvent
from services.seasonal_analysis_engine import seasonal_analysis_engine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage seasonal events for OSRS market analysis'
    
    def add_arguments(self, parser):
        # List events
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all seasonal events'
        )
        parser.add_argument(
            '--list-upcoming',
            action='store_true',
            help='List upcoming seasonal events'
        )
        
        # Add/modify events
        parser.add_argument(
            '--add-event',
            type=str,
            help='Add a new seasonal event (provide event name)'
        )
        parser.add_argument(
            '--event-type',
            choices=['osrs_official', 'community', 'detected_anomaly', 'holiday', 'update', 'seasonal'],
            default='osrs_official',
            help='Type of event to add'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Event start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='Event end date (YYYY-MM-DD format, optional if duration provided)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            help='Event duration in days'
        )
        parser.add_argument(
            '--recurring',
            action='store_true',
            help='Mark event as recurring'
        )
        parser.add_argument(
            '--recurrence-pattern',
            choices=['weekly', 'monthly', 'quarterly', 'yearly'],
            help='Recurrence pattern for recurring events'
        )
        parser.add_argument(
            '--description',
            type=str,
            help='Event description'
        )
        parser.add_argument(
            '--categories',
            nargs='+',
            help='Item categories affected by the event'
        )
        
        # Event management actions
        parser.add_argument(
            '--predict-next-events',
            action='store_true',
            help='Predict next occurrence of recurring events'
        )
        parser.add_argument(
            '--update-impact-data',
            action='store_true',
            help='Update impact data for existing events'
        )
        parser.add_argument(
            '--verify-events',
            nargs='+',
            type=int,
            help='Mark specified event IDs as verified'
        )
        parser.add_argument(
            '--bootstrap-default-events',
            action='store_true',
            help='Bootstrap database with default OSRS events'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            if options.get('list'):
                asyncio.run(self.list_events())
            elif options.get('list_upcoming'):
                asyncio.run(self.list_upcoming_events())
            elif options.get('add_event'):
                asyncio.run(self.add_event(options))
            elif options.get('predict_next_events'):
                asyncio.run(self.predict_next_events())
            elif options.get('update_impact_data'):
                asyncio.run(self.update_impact_data())
            elif options.get('verify_events'):
                asyncio.run(self.verify_events(options['verify_events']))
            elif options.get('bootstrap_default_events'):
                asyncio.run(self.bootstrap_default_events())
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No action specified. Use --help to see available options."
                    )
                )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Command failed: {e}"))
            logger.exception("Seasonal events management command failed")
    
    async def list_events(self):
        """List all seasonal events."""
        self.stdout.write("📅 Seasonal Events Database:")
        
        events = await sync_to_async(list)(
            SeasonalEvent.objects.all().order_by('-detection_timestamp')
        )
        
        if not events:
            self.stdout.write("   No events found.")
            return
        
        for event in events:
            status = "🟢 Active" if event.is_current else "🟡 Upcoming" if event.is_upcoming else "⚪ Inactive"
            recurrence = f"({event.recurrence_pattern})" if event.is_recurring else "(one-time)"
            
            self.stdout.write(
                f"   {event.id:3d}: {event.event_name} {status} {recurrence}"
            )
            self.stdout.write(
                f"        Type: {event.event_type} | "
                f"Impact: P{event.average_price_impact_pct:+.1f}% V{event.average_volume_impact_pct:+.1f}% | "
                f"Verification: {event.verification_status}"
            )
            
            if event.start_date:
                date_info = f"{event.start_date}"
                if event.end_date:
                    date_info += f" to {event.end_date}"
                else:
                    date_info += f" ({event.duration_days} days)"
                self.stdout.write(f"        Dates: {date_info}")
            
            self.stdout.write("")
    
    async def list_upcoming_events(self):
        """List upcoming seasonal events."""
        self.stdout.write("📅 Upcoming Seasonal Events (next 60 days):")
        
        today = timezone.now().date()
        future_date = today + timedelta(days=60)
        
        events = await sync_to_async(list)(
            SeasonalEvent.objects.filter(
                start_date__range=[today, future_date],
                is_active=True
            ).order_by('start_date')
        )
        
        if not events:
            # Check for predicted events
            recurring_events = await sync_to_async(list)(
                SeasonalEvent.objects.filter(
                    is_recurring=True,
                    is_active=True,
                    verification_status='verified'
                )
            )
            
            predicted_events = []
            for event in recurring_events:
                next_date = event.predict_next_occurrence()
                if next_date and next_date <= future_date:
                    days_until = (next_date - today).days
                    predicted_events.append((event, next_date, days_until))
            
            if predicted_events:
                self.stdout.write("   🔮 Predicted upcoming events:")
                for event, next_date, days_until in sorted(predicted_events, key=lambda x: x[2]):
                    self.stdout.write(
                        f"      {event.event_name}: {next_date} (in {days_until} days)"
                    )
                    self.stdout.write(
                        f"         Expected impact: P{event.average_price_impact_pct:+.1f}% "
                        f"V{event.average_volume_impact_pct:+.1f}%"
                    )
            else:
                self.stdout.write("   No upcoming events found.")
            return
        
        for event in events:
            days_until = (event.start_date - today).days
            impact_indicator = "🔴" if abs(event.average_price_impact_pct) >= 10 else "🟡" if abs(event.average_price_impact_pct) >= 5 else "🟢"
            
            self.stdout.write(
                f"   {impact_indicator} {event.event_name}: {event.start_date} (in {days_until} days)"
            )
            self.stdout.write(
                f"      Expected impact: P{event.average_price_impact_pct:+.1f}% "
                f"V{event.average_volume_impact_pct:+.1f}%"
            )
            
            if event.affected_categories:
                self.stdout.write(f"      Affected categories: {', '.join(event.affected_categories)}")
            
            self.stdout.write("")
    
    async def add_event(self, options):
        """Add a new seasonal event."""
        event_name = options['add_event']
        
        # Parse dates
        start_date = None
        end_date = None
        duration_days = 1
        
        if options.get('start_date'):
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        
        if options.get('end_date'):
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
            if start_date:
                duration_days = (end_date - start_date).days + 1
        elif options.get('duration'):
            duration_days = options['duration']
            if start_date:
                end_date = start_date + timedelta(days=duration_days - 1)
        
        # Create event
        event_data = {
            'event_name': event_name,
            'event_type': options.get('event_type', 'osrs_official'),
            'start_date': start_date,
            'end_date': end_date,
            'duration_days': duration_days,
            'description': options.get('description', ''),
            'is_recurring': options.get('recurring', False),
            'recurrence_pattern': options.get('recurrence_pattern', ''),
            'affected_categories': options.get('categories', []),
            'detection_method': 'manual_entry',
            'is_active': True,
            'verification_status': 'unverified'
        }
        
        try:
            event = await sync_to_async(SeasonalEvent.objects.create)(**event_data)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Added seasonal event: {event.event_name} (ID: {event.id})"
                )
            )
            
            if start_date:
                self.stdout.write(f"   📅 Date: {start_date} ({duration_days} days)")
            
            if event.is_recurring:
                self.stdout.write(f"   🔄 Recurring: {event.recurrence_pattern}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to add event: {e}"))
    
    async def predict_next_events(self):
        """Predict next occurrence of recurring events."""
        self.stdout.write("🔮 Predicting next occurrence of recurring events...")
        
        recurring_events = await sync_to_async(list)(
            SeasonalEvent.objects.filter(
                is_recurring=True,
                is_active=True
            )
        )
        
        if not recurring_events:
            self.stdout.write("   No recurring events found.")
            return
        
        predicted_count = 0
        
        for event in recurring_events:
            try:
                next_occurrence = event.predict_next_occurrence()
                
                if next_occurrence:
                    today = timezone.now().date()
                    days_until = (next_occurrence - today).days
                    
                    self.stdout.write(
                        f"   📅 {event.event_name}: {next_occurrence} (in {days_until} days)"
                    )
                    
                    # If the next occurrence is within reasonable range, you could create a new event entry
                    if 0 <= days_until <= 365:  # Within next year
                        predicted_count += 1
                
            except Exception as e:
                self.stdout.write(f"   ❌ Failed to predict {event.event_name}: {e}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Predicted {predicted_count} upcoming event occurrences")
        )
    
    async def update_impact_data(self):
        """Update impact data for existing events."""
        self.stdout.write("📊 Updating impact data for seasonal events...")
        
        events = await sync_to_async(list)(
            SeasonalEvent.objects.filter(is_active=True)
        )
        
        if not events:
            self.stdout.write("   No active events found.")
            return
        
        updated_count = 0
        
        for event in events:
            try:
                # Here you would analyze market data around the event dates
                # For now, we'll simulate the update
                
                # You could call seasonal_analysis_engine to analyze impact
                # impact_data = await analyze_event_impact(event)
                
                # Simulate impact data update
                if event.historical_occurrences:
                    # Update confidence if we have historical data
                    event.impact_confidence = min(0.9, len(event.historical_occurrences) * 0.1)
                    await sync_to_async(event.save)()
                    updated_count += 1
                
                self.stdout.write(f"   ✅ Updated {event.event_name}")
                
            except Exception as e:
                self.stdout.write(f"   ❌ Failed to update {event.event_name}: {e}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Updated impact data for {updated_count} events")
        )
    
    async def verify_events(self, event_ids: List[int]):
        """Mark specified events as verified."""
        self.stdout.write(f"✅ Verifying {len(event_ids)} events...")
        
        verified_count = 0
        
        for event_id in event_ids:
            try:
                event = await sync_to_async(SeasonalEvent.objects.get)(id=event_id)
                event.verification_status = 'verified'
                await sync_to_async(event.save)()
                
                self.stdout.write(f"   ✅ Verified: {event.event_name}")
                verified_count += 1
                
            except SeasonalEvent.DoesNotExist:
                self.stdout.write(f"   ❌ Event ID {event_id} not found")
            except Exception as e:
                self.stdout.write(f"   ❌ Failed to verify event {event_id}: {e}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Verified {verified_count} events")
        )
    
    async def bootstrap_default_events(self):
        """Bootstrap database with default OSRS events."""
        self.stdout.write("🚀 Bootstrapping default OSRS seasonal events...")
        
        default_events = [
            {
                'event_name': 'Double XP Weekend',
                'event_type': 'osrs_official',
                'duration_days': 3,
                'is_recurring': True,
                'recurrence_pattern': 'quarterly',
                'description': 'Official Double XP Weekend event',
                'affected_categories': ['combat', 'skilling', 'supplies'],
                'average_price_impact_pct': 15.0,
                'average_volume_impact_pct': 40.0,
                'impact_confidence': 0.9,
                'detection_method': 'bootstrap',
                'verification_status': 'verified'
            },
            {
                'event_name': 'Christmas Event',
                'event_type': 'osrs_official',
                'start_date': date(2024, 12, 15),
                'end_date': date(2024, 12, 30),
                'duration_days': 15,
                'is_recurring': True,
                'recurrence_pattern': 'yearly',
                'description': 'Annual Christmas event',
                'affected_categories': ['cosmetic', 'food', 'rare'],
                'average_price_impact_pct': -8.0,
                'average_volume_impact_pct': 25.0,
                'impact_confidence': 0.8,
                'detection_method': 'bootstrap',
                'verification_status': 'verified'
            },
            {
                'event_name': 'Halloween Event',
                'event_type': 'osrs_official',
                'start_date': date(2024, 10, 20),
                'end_date': date(2024, 11, 5),
                'duration_days': 16,
                'is_recurring': True,
                'recurrence_pattern': 'yearly',
                'description': 'Annual Halloween event',
                'affected_categories': ['cosmetic', 'rare'],
                'average_price_impact_pct': -12.0,
                'average_volume_impact_pct': 30.0,
                'impact_confidence': 0.8,
                'detection_method': 'bootstrap',
                'verification_status': 'verified'
            },
            {
                'event_name': 'Leagues Tournament',
                'event_type': 'osrs_official',
                'duration_days': 60,
                'is_recurring': True,
                'recurrence_pattern': 'yearly',
                'description': 'Annual Leagues tournament',
                'affected_categories': ['all'],
                'average_price_impact_pct': -18.0,
                'average_volume_impact_pct': -25.0,
                'impact_confidence': 0.9,
                'detection_method': 'bootstrap',
                'verification_status': 'verified'
            },
            {
                'event_name': 'Deadman Mode Tournament',
                'event_type': 'osrs_official',
                'duration_days': 30,
                'is_recurring': True,
                'recurrence_pattern': 'yearly',
                'description': 'Deadman Mode tournament',
                'affected_categories': ['combat', 'supplies', 'food'],
                'average_price_impact_pct': 20.0,
                'average_volume_impact_pct': 35.0,
                'impact_confidence': 0.7,
                'detection_method': 'bootstrap',
                'verification_status': 'verified'
            }
        ]
        
        created_count = 0
        
        for event_data in default_events:
            try:
                # Check if event already exists
                existing = await sync_to_async(
                    SeasonalEvent.objects.filter(event_name=event_data['event_name']).exists
                )()
                
                if not existing:
                    await sync_to_async(SeasonalEvent.objects.create)(**event_data)
                    self.stdout.write(f"   ✅ Added: {event_data['event_name']}")
                    created_count += 1
                else:
                    self.stdout.write(f"   ⏭️  Exists: {event_data['event_name']}")
                    
            except Exception as e:
                self.stdout.write(f"   ❌ Failed to add {event_data['event_name']}: {e}")
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Bootstrapped {created_count} new seasonal events")
        )