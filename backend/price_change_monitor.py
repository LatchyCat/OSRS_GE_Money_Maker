
# Add this to your price processing pipeline

def monitor_price_changes(item_name: str, old_price: int, new_price: int):
    """Monitor for suspicious price changes."""
    import logging
    logger = logging.getLogger(__name__)
    
    if old_price and new_price and old_price > 0:
        change_ratio = new_price / old_price
        
        # Flag major price changes
        if change_ratio > 10 or change_ratio < 0.1:
            logger.warning(f"Major price change for {item_name}: "
                          f"{old_price:,} -> {new_price:,} GP "
                          f"({change_ratio:.1f}x change)")
            
            # Could trigger additional validation or admin alerts here
            return True
    
    return False
