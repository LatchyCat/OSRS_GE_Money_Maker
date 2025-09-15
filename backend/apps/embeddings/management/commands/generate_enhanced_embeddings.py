"""
Management command for generating enhanced embeddings with volume data and confidence scoring.

This command uses the snowflake-arctic-embed2:latest model to create AI-ready embeddings
that include comprehensive trading context, volume analysis, and confidence metrics.
"""

import asyncio
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from services.enhanced_embedding_service import EnhancedEmbeddingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate enhanced embeddings with volume data and comprehensive trading context'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--items',
            type=str,
            help='Comma-separated list of item IDs to generate embeddings for'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate embeddings even if they already exist'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of items to process per batch (default: 10)'
        )
        
        parser.add_argument(
            '--max-items',
            type=int,
            help='Maximum number of items to process (for testing)'
        )
        
        parser.add_argument(
            '--test-single',
            type=int,
            help='Test embedding generation for a single item ID'
        )
        
        parser.add_argument(
            '--check-model',
            action='store_true',
            help='Check if the embedding model is available in Ollama'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose logging'
        )
    
    def handle(self, *args, **options):
        # Configure logging
        if options['verbose']:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
            logger.setLevel(logging.INFO)
        
        # Run async command handler
        asyncio.run(self._async_handle(options))
    
    async def _async_handle(self, options):
        """Async handler for the management command."""
        start_time = timezone.now()
        
        # Initialize enhanced embedding service
        embedding_service = EnhancedEmbeddingService()
        
        # Model check mode
        if options['check_model']:
            await self._check_model_availability(embedding_service)
            return
        
        # Single item test mode
        if options['test_single']:
            await self._test_single_item_embedding(embedding_service, options['test_single'])
            return
        
        # Parse item IDs if provided
        item_ids = None
        if options['items']:
            try:
                item_ids = [int(x.strip()) for x in options['items'].split(',')]
                self.stdout.write(f"Targeting {len(item_ids)} specific items")
            except ValueError as e:
                raise CommandError(f"Invalid item IDs format: {e}")
        
        # Apply max items limit
        if options['max_items'] and item_ids:
            item_ids = item_ids[:options['max_items']]
            self.stdout.write(f"Limited to first {len(item_ids)} items")
        
        try:
            self.stdout.write(self.style.SUCCESS("🚀 Starting enhanced embedding generation..."))
            
            # Set batch size if provided
            if options['batch_size']:
                embedding_service.batch_size = options['batch_size']
            
            if item_ids:
                # Generate embeddings for specific items
                results = await embedding_service.batch_generate_embeddings(
                    item_ids, 
                    save_to_db=True
                )
                
                await self._display_batch_results(results, start_time, options)
            else:
                # Regenerate all embeddings
                results = await embedding_service.regenerate_all_embeddings(
                    force=options['force']
                )
                
                await self._display_regeneration_results(results, start_time, options)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Embedding generation failed: {e}"))
            if options['verbose']:
                import traceback
                self.stdout.write(traceback.format_exc())
            raise CommandError(f"Embedding generation failed: {e}")
    
    async def _check_model_availability(self, embedding_service):
        """Check if the embedding model is available."""
        self.stdout.write("🔍 Checking embedding model availability...")
        
        try:
            available = await embedding_service.ensure_model_available()
            
            if available:
                self.stdout.write(self.style.SUCCESS("✅ Embedding model is available"))
                self.stdout.write(f"   Model: {embedding_service.model_name}")
                self.stdout.write(f"   Ollama URL: {embedding_service.base_url}")
                
                # Test a simple embedding
                self.stdout.write("🧪 Testing embedding generation...")
                test_response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: embedding_service.client.embeddings(
                        model=embedding_service.model_name,
                        prompt="test embedding"
                    )
                )
                
                if 'embedding' in test_response:
                    embedding_dim = len(test_response['embedding'])
                    self.stdout.write(self.style.SUCCESS(f"✅ Test embedding successful ({embedding_dim} dimensions)"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Test embedding failed - no embedding in response"))
                    
            else:
                self.stdout.write(self.style.ERROR("❌ Embedding model is not available"))
                self.stdout.write("   Try running: ollama pull snowflake-arctic-embed2:latest")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Model check failed: {e}"))
    
    async def _test_single_item_embedding(self, embedding_service, item_id):
        """Test embedding generation for a single item."""
        self.stdout.write(f"🧪 Testing enhanced embedding for item {item_id}...")
        
        try:
            # Ensure model is available
            if not await embedding_service.ensure_model_available():
                raise Exception("Embedding model not available")
            
            # Build context
            context = await embedding_service._build_embedding_context(item_id)
            
            # Show context details
            self.stdout.write("📋 Embedding Context:")
            if context.item_metadata:
                self.stdout.write(f"   Item: {context.item_metadata.name}")
                self.stdout.write(f"   Members: {context.item_metadata.members}")
                self.stdout.write(f"   High Alch: {context.item_metadata.highalch:,} GP")
            
            if context.price_data:
                self.stdout.write(f"   High Price: {context.price_data.high_price:,} GP")
                self.stdout.write(f"   Low Price: {context.price_data.low_price:,} GP")
                self.stdout.write(f"   Volume: {context.price_data.total_volume:,}")
                self.stdout.write(f"   Data Age: {context.price_data.age_hours:.1f}h")
            
            if context.confidence_components:
                conf = context.confidence_components
                self.stdout.write(f"   Confidence: {conf.total_score:.2f} ({conf.quality_grade})")
            
            if context.trading_tags:
                self.stdout.write(f"   Tags: {', '.join(context.trading_tags[:10])}")
            
            # Generate embedding text
            embedding_text = embedding_service.create_comprehensive_embedding_text(context)
            self.stdout.write(f"📝 Embedding Text ({len(embedding_text)} chars):")
            # Show truncated version
            preview_text = embedding_text[:300] + "..." if len(embedding_text) > 300 else embedding_text
            self.stdout.write(f"   {preview_text}")
            
            # Generate actual embedding
            embedding = await embedding_service.generate_enhanced_embedding(item_id)
            
            if embedding is not None:
                self.stdout.write(self.style.SUCCESS(f"✅ Generated embedding: {embedding.shape}"))
                self.stdout.write(f"   Dimensions: {embedding.shape[0]}")
                self.stdout.write(f"   Value range: [{embedding.min():.4f}, {embedding.max():.4f}]")
                self.stdout.write(f"   Mean: {embedding.mean():.4f}")
                
                # Save to database
                await embedding_service._save_embedding_to_db(item_id, embedding)
                self.stdout.write("💾 Saved to database")
            else:
                self.stdout.write(self.style.ERROR("❌ Failed to generate embedding"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {e}"))
    
    async def _display_batch_results(self, results, start_time, options):
        """Display results from batch embedding generation."""
        successful_count = sum(1 for emb in results.values() if emb is not None)
        failed_count = len(results) - successful_count
        
        # Calculate timing
        end_time = timezone.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Display summary
        self.stdout.write(self.style.SUCCESS("✅ Enhanced embedding generation completed!"))
        self.stdout.write("")
        
        # Statistics
        self.stdout.write("📊 Generation Statistics:")
        self.stdout.write(f"   Total items processed: {len(results):,}")
        self.stdout.write(f"   Successful embeddings: {successful_count:,}")
        self.stdout.write(f"   Failed embeddings: {failed_count:,}")
        self.stdout.write(f"   Success rate: {(successful_count/len(results)*100):.1f}%")
        self.stdout.write("")
        
        # Performance metrics
        self.stdout.write("⚡ Performance Metrics:")
        self.stdout.write(f"   Total processing time: {total_time:.1f} seconds")
        if total_time > 0:
            items_per_minute = (len(results) / total_time) * 60
            self.stdout.write(f"   Items per minute: {items_per_minute:.1f}")
        self.stdout.write("")
        
        # Quality assessment
        success_rate = (successful_count / len(results)) * 100 if results else 0
        if success_rate >= 95:
            quality_indicator = self.style.SUCCESS("🟢 Excellent")
        elif success_rate >= 85:
            quality_indicator = self.style.WARNING("🟡 Good")  
        else:
            quality_indicator = self.style.ERROR("🔴 Needs Attention")
        
        self.stdout.write(f"📈 Generation Quality: {quality_indicator} ({success_rate:.1f}%)")
    
    async def _display_regeneration_results(self, results, start_time, options):
        """Display results from full regeneration."""
        # Calculate timing
        end_time = timezone.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Display summary based on results
        if results['status'] == 'completed':
            self.stdout.write(self.style.SUCCESS("✅ Enhanced embedding regeneration completed!"))
            self.stdout.write("")
            
            # Statistics
            self.stdout.write("📊 Regeneration Statistics:")
            self.stdout.write(f"   Total items processed: {results.get('total_items', 0):,}")
            self.stdout.write(f"   Successful embeddings: {results.get('successful_embeddings', 0):,}")
            self.stdout.write(f"   Failed embeddings: {results.get('failed_embeddings', 0):,}")
            self.stdout.write(f"   Success rate: {results.get('success_rate', 0):.1f}%")
            self.stdout.write("")
            
            # Performance
            self.stdout.write("⚡ Performance Metrics:")
            self.stdout.write(f"   Total processing time: {total_time:.1f} seconds")
            if total_time > 0 and results.get('total_items', 0) > 0:
                items_per_minute = (results['total_items'] / total_time) * 60
                self.stdout.write(f"   Items per minute: {items_per_minute:.1f}")
            
        else:
            self.stdout.write(self.style.ERROR(f"❌ Regeneration failed: {results.get('error', 'Unknown error')}"))
        
        # Next steps
        self.stdout.write("")
        self.stdout.write("🎯 Next Steps:")
        self.stdout.write("   1. Rebuild FAISS indices with new embeddings")
        self.stdout.write("   2. Test similarity search functionality")
        self.stdout.write("   3. Set up periodic embedding updates")
        
        # Useful commands
        self.stdout.write("")
        self.stdout.write("📝 Useful Commands:")
        self.stdout.write("   - Model check: python manage.py generate_enhanced_embeddings --check-model")
        self.stdout.write("   - Test single item: python manage.py generate_enhanced_embeddings --test-single 995")
        self.stdout.write("   - Force regenerate: python manage.py generate_enhanced_embeddings --force")