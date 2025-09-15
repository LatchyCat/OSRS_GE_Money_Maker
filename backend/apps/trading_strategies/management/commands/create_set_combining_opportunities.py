from django.core.management.base import BaseCommand
from apps.trading_strategies.services.set_combining_analyzer import SetCombiningAnalyzer
from apps.items.models import Item
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create set combining opportunities with correct OSRS item IDs'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing set combining opportunities before creating new ones',
        )
        parser.add_argument(
            '--min-profit',
            type=int,
            default=50000,
            help='Minimum profit in GP (default: 50000)',
        )
        parser.add_argument(
            '--min-margin',
            type=float,
            default=2.0,
            help='Minimum profit margin percentage (default: 2.0)',
        )
    
    def handle(self, *args, **options):
        if options['clear_existing']:
            from apps.trading_strategies.models import SetCombiningOpportunity
            deleted_count = SetCombiningOpportunity.objects.all().delete()[0]
            self.stdout.write(f"🗑️  Cleared {deleted_count} existing set combining opportunities")
        
        self.stdout.write("🔍 Looking up correct item IDs from database...")
        
        # Get correct item IDs from the database
        corrected_sets = self._get_corrected_set_combinations()
        
        # Create custom analyzer with corrected IDs
        analyzer = SetCombiningAnalyzer(
            min_lazy_tax=options['min_profit'],
            min_margin_pct=options['min_margin']
        )
        
        # Override the hardcoded set combinations with correct IDs
        analyzer.SET_COMBINATIONS = corrected_sets
        
        self.stdout.write(f"📊 Analyzing {len(corrected_sets)} armor/weapon sets...")
        self.stdout.write(f"💰 Minimum profit: {options['min_profit']:,} GP")
        self.stdout.write(f"📈 Minimum margin: {options['min_margin']}%")
        
        # Analyze and create opportunities
        opportunities = analyzer.analyze_opportunities()
        
        if opportunities:
            created_count = analyzer.create_strategy_opportunities(opportunities)
            
            self.stdout.write(self.style.SUCCESS(
                f"✅ Successfully created {created_count} set combining opportunities!"
            ))
            
            # Show summary of created opportunities
            self.stdout.write("\n📈 Top opportunities created:")
            for i, opp in enumerate(opportunities[:5], 1):
                profit = opp['lazy_tax_profit']
                margin = opp['margin_pct']
                self.stdout.write(f"  {i}. {opp['set_name']}: {profit:,} GP ({margin:.1f}% margin)")
                
        else:
            self.stdout.write(self.style.WARNING(
                "⚠️  No profitable set combining opportunities found with current criteria"
            ))
            self.stdout.write("💡 Try lowering minimum profit or margin requirements")
    
    def _get_corrected_set_combinations(self):
        """Get set combinations with correct item IDs from the database"""
        
        # Function to find item by name pattern
        def find_item_id(name_pattern):
            items = Item.objects.filter(name__icontains=name_pattern)
            if items.exists():
                # Prefer items without " 0" suffix (broken/degraded items)
                non_degraded = items.exclude(name__endswith=' 0')
                if non_degraded.exists():
                    return non_degraded.first().id
                return items.first().id
            return None
        
        corrected_sets = {}
        
        # Barrows sets with corrected IDs
        barrows_brothers = [
            ('Dharok', ['helm', 'platebody', 'platelegs', 'greataxe']),
            ('Ahrim', ['hood', 'robetop', 'robeskirt', 'staff']),
            ('Guthan', ['helm', 'platebody', 'chainskirt', 'warspear']),
            ('Karil', ['coif', 'leathertop', 'leatherskirt', 'crossbow']),
            ('Torag', ['helm', 'platebody', 'platelegs', 'hammers']),
            ('Verac', ['helm', 'brassard', 'plateskirt', 'flail']),
        ]
        
        for brother_name, piece_names in barrows_brothers:
            # Find the complete set
            set_item_id = find_item_id(f"{brother_name}'s armour set")
            
            # Find individual pieces
            pieces = []
            for piece_name in piece_names:
                piece_id = find_item_id(f"{brother_name}'s {piece_name}")
                if piece_id:
                    pieces.append({
                        'id': piece_id,
                        'name': f"{brother_name}'s {piece_name}"
                    })
            
            if len(pieces) >= 3:  # Need at least 3 pieces for a meaningful set
                corrected_sets[f"{brother_name}'s set"] = {
                    'set_item_id': set_item_id,
                    'pieces': pieces
                }
        
        # God Wars Dungeon sets
        gwd_sets = [
            ('Bandos', ['chestplate', 'tassets', 'boots']),
            ('Armadyl', ['helmet', 'chestplate', 'chainskirt']),
            ('Zamorak', ['helm', 'chestplate', 'chainskirt']),  # Subjugation
            ('Saradomin', ['mitre', 'robe top', 'robe bottom']),  # Vestments
        ]
        
        for god_name, piece_names in gwd_sets:
            pieces = []
            for piece_name in piece_names:
                # Try different name patterns
                patterns = [
                    f"{god_name} {piece_name}",
                    f"{god_name}'s {piece_name}",
                ]
                
                piece_id = None
                for pattern in patterns:
                    piece_id = find_item_id(pattern)
                    if piece_id:
                        break
                
                if piece_id:
                    item_name = Item.objects.get(id=piece_id).name
                    pieces.append({
                        'id': piece_id,
                        'name': item_name
                    })
            
            if len(pieces) >= 2:  # GWD sets can be profitable with fewer pieces
                corrected_sets[f"{god_name} set"] = {
                    'set_item_id': None,  # Most GWD sets don't have official set items
                    'pieces': pieces
                }
        
        # Dragon hide sets
        dhide_colors = ['Green', 'Blue', 'Red', 'Black']
        for color in dhide_colors:
            pieces = []
            for piece_type in ['body', 'chaps', 'vambraces']:
                piece_id = find_item_id(f"{color} d'hide {piece_type}")
                if piece_id:
                    item_name = Item.objects.get(id=piece_id).name
                    pieces.append({
                        'id': piece_id,
                        'name': item_name
                    })
            
            if len(pieces) >= 3:
                corrected_sets[f"{color} d'hide set"] = {
                    'set_item_id': None,
                    'pieces': pieces
                }
        
        # Void sets
        void_types = ['melee', 'ranger', 'mage']
        for void_type in void_types:
            pieces = []
            
            # Void helm specific to type
            helm_id = find_item_id(f"Void {void_type} helm")
            if helm_id:
                pieces.append({'id': helm_id, 'name': f"Void {void_type} helm"})
            
            # Common void pieces
            for common_piece in ['knight top', 'knight robe', 'knight gloves']:
                piece_id = find_item_id(f"Void {common_piece}")
                if piece_id:
                    item_name = Item.objects.get(id=piece_id).name
                    pieces.append({
                        'id': piece_id,
                        'name': item_name
                    })
            
            if len(pieces) >= 4:
                corrected_sets[f"Void {void_type} set"] = {
                    'set_item_id': None,
                    'pieces': pieces
                }
        
        # Fighter torso sets (if available)
        fighter_pieces = []
        for piece_name in ['torso', 'hat']:
            piece_id = find_item_id(f"Fighter {piece_name}")
            if piece_id:
                item_name = Item.objects.get(id=piece_id).name
                fighter_pieces.append({
                    'id': piece_id,
                    'name': item_name
                })
        
        if fighter_pieces:
            corrected_sets["Fighter set"] = {
                'set_item_id': None,
                'pieces': fighter_pieces
            }
        
        self.stdout.write(f"✅ Found {len(corrected_sets)} sets with correct item IDs:")
        for set_name, set_data in corrected_sets.items():
            piece_count = len(set_data['pieces'])
            has_set_item = "✓" if set_data['set_item_id'] else "✗"
            self.stdout.write(f"  • {set_name}: {piece_count} pieces, set item: {has_set_item}")
        
        return corrected_sets