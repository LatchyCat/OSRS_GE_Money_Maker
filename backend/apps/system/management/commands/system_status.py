"""
Django management command to display comprehensive system status.
Shows system health, data freshness, and sync history.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Avg, Max, Min
from datetime import timedelta

from apps.system.models import SystemState, SyncOperation
from apps.items.models import Item
from apps.prices.models import PriceSnapshot, ProfitCalculation


class Command(BaseCommand):
    help = 'Display comprehensive system status and health metrics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed breakdown of all metrics'
        )
        parser.add_argument(
            '--sync-history',
            action='store_true',
            help='Show recent sync operation history'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('📊 OSRS High Alch Tracker - System Status')
        )
        self.stdout.write("=" * 60)
        
        try:
            # Get system state
            try:
                system_state = SystemState.objects.get(id=1)
            except SystemState.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR("❌ No system state found - run startup sync first")
                )
                return
            
            # Display main status
            self._display_main_status(system_state)
            
            # Display data metrics
            self._display_data_metrics(system_state, options.get('detailed', False))
            
            # Display sync status
            self._display_sync_status(system_state)
            
            # Display sync history if requested
            if options.get('sync_history'):
                self._display_sync_history()
            
            # Display recommendations
            self._display_recommendations(system_state)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error displaying status: {e}")
            )
            raise
    
    def _display_main_status(self, system_state):
        """Display main system status."""
        # System uptime info
        uptime_hours = (timezone.now() - system_state.last_startup_time).total_seconds() / 3600
        
        self.stdout.write("\n🚀 System Status:")
        self.stdout.write(f"   • Status: {'🔄 Syncing' if system_state.sync_in_progress else '✅ Running'}")
        self.stdout.write(f"   • Startup #{system_state.startup_count}")
        self.stdout.write(f"   • Last startup: {system_state.last_startup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write(f"   • Uptime: {uptime_hours:.1f} hours")
        self.stdout.write(f"   • Last downtime: {system_state.downtime_hours:.2f} hours")
        
        # Data quality
        quality_color = self.style.SUCCESS
        if system_state.data_quality_score < 50:
            quality_color = self.style.ERROR
        elif system_state.data_quality_score < 80:
            quality_color = self.style.WARNING
        
        self.stdout.write(f"   • Data quality: {quality_color(f'{system_state.data_quality_score:.1f}/100')}")
    
    def _display_data_metrics(self, system_state, detailed=False):
        """Display data metrics and statistics."""
        self.stdout.write("\n📊 Data Metrics:")
        
        # Item counts
        self.stdout.write(f"   • Total items: {system_state.total_items_count:,}")
        self.stdout.write(f"   • Profitable items: {system_state.profitable_items_count:,}")
        self.stdout.write(f"   • New items discovered: {system_state.new_items_discovered:,}")
        
        if detailed:
            # Additional detailed metrics
            self._display_detailed_metrics()
    
    def _display_detailed_metrics(self):
        """Display detailed data breakdown."""
        self.stdout.write("\n🔍 Detailed Metrics:")
        
        # Item breakdown
        total_items = Item.objects.count()
        active_items = Item.objects.filter(is_active=True).count()
        members_items = Item.objects.filter(members=True, is_active=True).count()
        f2p_items = Item.objects.filter(members=False, is_active=True).count()
        
        self.stdout.write(f"   • Active items: {active_items:,} / {total_items:,}")
        self.stdout.write(f"   • Members items: {members_items:,}")
        self.stdout.write(f"   • F2P items: {f2p_items:,}")
        
        # Price data metrics
        recent_prices = PriceSnapshot.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        total_profit_calcs = ProfitCalculation.objects.count()
        profitable_calcs = ProfitCalculation.objects.filter(
            current_profit__gt=0
        ).count()
        
        self.stdout.write(f"   • Recent price updates: {recent_prices:,}")
        self.stdout.write(f"   • Items with profit data: {total_profit_calcs:,}")
        self.stdout.write(f"   • Currently profitable: {profitable_calcs:,}")
        
        # Profit statistics
        if profitable_calcs > 0:
            profit_stats = ProfitCalculation.objects.filter(
                current_profit__gt=0
            ).aggregate(
                avg_profit=Avg('current_profit'),
                max_profit=Max('current_profit'),
                min_profit=Min('current_profit')
            )
            
            self.stdout.write(f"   • Average profit: {profit_stats['avg_profit']:.0f} gp")
            self.stdout.write(f"   • Max profit: {profit_stats['max_profit']:.0f} gp")
            self.stdout.write(f"   • Min profit: {profit_stats['min_profit']:.0f} gp")
    
    def _display_sync_status(self, system_state):
        """Display sync status and freshness."""
        self.stdout.write("\n🔄 Sync Status:")
        
        now = timezone.now()
        
        # Helper function to format time ago
        def time_ago(dt):
            if not dt:
                return "Never"
            diff = now - dt
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            else:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
        
        # Display sync times with freshness indicators
        syncs = [
            ("Full sync", system_state.last_full_sync, 24),  # 24 hour threshold
            ("Price sync", system_state.last_price_sync, 1),   # 1 hour threshold  
            ("Item mapping", system_state.last_item_mapping_sync, 168), # 7 days
            ("Embeddings", system_state.last_embedding_sync, 336), # 14 days
        ]
        
        for name, last_sync, stale_hours in syncs:
            time_str = time_ago(last_sync)
            
            # Determine freshness
            if not last_sync:
                status = self.style.ERROR("❌")
            else:
                hours_since = (now - last_sync).total_seconds() / 3600
                if hours_since < stale_hours / 2:
                    status = self.style.SUCCESS("✅")
                elif hours_since < stale_hours:
                    status = self.style.WARNING("⚠️")
                else:
                    status = self.style.ERROR("❌")
            
            self.stdout.write(f"   • {name}: {status} {time_str}")
        
        # Current sync strategy
        if system_state.sync_in_progress:
            self.stdout.write(f"   • Current strategy: 🔄 {system_state.current_sync_strategy}")
        else:
            recommended = system_state.determine_sync_strategy()
            if recommended != 'none':
                self.stdout.write(f"   • Recommended: ⚠️ {recommended}")
            else:
                self.stdout.write("   • Status: ✅ All data fresh")
    
    def _display_sync_history(self):
        """Display recent sync operation history."""
        self.stdout.write("\n📋 Recent Sync History:")
        
        recent_ops = SyncOperation.objects.order_by('-started_at')[:10]
        
        if not recent_ops:
            self.stdout.write("   • No sync operations found")
            return
        
        for op in recent_ops:
            # Status emoji
            status_emoji = {
                'completed': '✅',
                'failed': '❌', 
                'in_progress': '🔄',
                'started': '🟡',
                'cancelled': '🟠'
            }.get(op.status, '❓')
            
            # Format duration
            if op.duration_seconds:
                if op.duration_seconds < 60:
                    duration = f"{op.duration_seconds:.1f}s"
                else:
                    duration = f"{op.duration_seconds/60:.1f}m"
            else:
                duration = "N/A"
            
            # Main operation line
            self.stdout.write(
                f"   {status_emoji} {op.get_operation_type_display()} "
                f"({op.started_at.strftime('%m/%d %H:%M')}) - {duration}"
            )
            
            # Success details
            if op.status == 'completed' and (op.items_processed or op.items_created):
                details = []
                if op.items_processed:
                    details.append(f"{op.items_processed} processed")
                if op.items_created:
                    details.append(f"{op.items_created} created") 
                if op.items_updated:
                    details.append(f"{op.items_updated} updated")
                if op.errors_encountered:
                    details.append(f"{op.errors_encountered} errors")
                
                if details:
                    self.stdout.write(f"     └─ {', '.join(details)}")
            
            # Error details
            elif op.status == 'failed' and op.error_message:
                error_msg = op.error_message[:60] + "..." if len(op.error_message) > 60 else op.error_message
                self.stdout.write(f"     └─ Error: {error_msg}")
    
    def _display_recommendations(self, system_state):
        """Display system recommendations."""
        recommendations = []
        
        # Data quality recommendations
        if system_state.data_quality_score < 50:
            recommendations.append("🔧 Run complete_rebuild to improve data quality")
        elif system_state.data_quality_score < 80:
            recommendations.append("🔄 Run full_refresh to update stale data")
        
        # Sync recommendations
        recommended_strategy = system_state.determine_sync_strategy()
        if recommended_strategy != 'none':
            recommendations.append(f"⏰ Run {recommended_strategy} sync to refresh data")
        
        # Item count recommendations
        if system_state.total_items_count < 4000:
            recommendations.append("📦 Run item mapping sync to discover new items")
        
        # Profit data recommendations  
        if system_state.profitable_items_count == 0:
            recommendations.append("💰 Run price sync to calculate profit opportunities")
        
        if recommendations:
            self.stdout.write("\n💡 Recommendations:")
            for rec in recommendations:
                self.stdout.write(f"   • {rec}")
        else:
            self.stdout.write(f"\n✅ {self.style.SUCCESS('System is healthy - no actions needed!')}")