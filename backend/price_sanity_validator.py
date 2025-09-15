
def validate_and_sanitize_price(item_name: str, price: int, source: str = "unknown") -> dict:
    """
    Validate and potentially sanitize a price before storing in database.
    
    Args:
        item_name: Name of the item
        price: Price to validate
        source: Data source (for logging)
        
    Returns:
        Dict with sanitized price and validation info
    """
    from price_validation_fix import validate_price_sanity
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Validate price sanity
    validation = validate_price_sanity(item_name, price)
    
    if validation['severity'] in ['critical', 'major']:
        logger.warning(f"Price sanity check failed for {item_name}: {validation['issue']} "
                      f"(source: {source}, deviation: {validation['deviation_ratio']:.1f}x)")
        
        # For critical issues (>100x off), reject the price
        if validation['severity'] == 'critical':
            logger.error(f"REJECTING price for {item_name}: {price:,} GP is "
                        f"{validation['deviation_ratio']:.0f}x outside realistic range")
            return {
                'accepted': False,
                'original_price': price,
                'sanitized_price': None,
                'reason': f"Price {validation['deviation_ratio']:.0f}x outside realistic range",
                'validation': validation
            }
        
        # For major issues (10-100x off), flag but potentially accept
        logger.warning(f"FLAGGING price for {item_name}: {price:,} GP is "
                      f"{validation['deviation_ratio']:.1f}x outside expected range")
    
    return {
        'accepted': True,
        'original_price': price,
        'sanitized_price': price,
        'reason': None if validation['is_valid'] else validation['issue'],
        'validation': validation
    }
