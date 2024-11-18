# app/utils/validate_bot.py
from flask import current_app

def validate_bot_for_activation(bot, category):
    """Validate if a bot has all required components for successful execution.
    
    Validates based on:
    1. Required bot fields for basic operation
    2. Required fields for DALL-E image generation
    3. Required fields for article processing
    4. Required fields for Slack notifications
    5. Site configuration for RSS feeds
    6. Keyword and blacklist configuration
    
    Args:
        bot: Bot instance to validate
        category: Category instance associated with the bot
    
    Returns:
        list: List of validation errors, empty if validation successful
    """
    validation_errors = []
    
    # Essential bot fields
    if not bot:
        return ["Bot instance is required"]
    
    current_app.logger.debug(f"Validating Bot: '{bot.name}' (ID: {bot.id})")
    
    # Core bot configuration
    required_bot_fields = {
        'name': 'Bot name',
        'run_frequency': 'Run frequency',
        'prompt': 'Article processing prompt',
        'dalle_prompt': 'DALL-E image generation prompt'
    }
    
    for field, display_name in required_bot_fields.items():
        if not getattr(bot, field, None):
            error = f"Missing {display_name}"
            validation_errors.append(error)
            current_app.logger.debug(f"Validation failed: {error}")
    
    # Site validation (RSS feed)
    if not bot.sites:
        error = "No RSS feed site configured"
        validation_errors.append(error)
        current_app.logger.debug(f"Validation failed: {error}")
    elif not bot.sites[0].url:
        error = "RSS feed URL not configured"
        validation_errors.append(error)
        current_app.logger.debug(f"Validation failed: {error}")
    
    # Keywords validation (required for article filtering)
    if not bot.keywords:
        error = "No keywords configured for article filtering"
        validation_errors.append(error)
        current_app.logger.debug(f"Validation failed: {error}")
    
    # Blacklist validation (required for article filtering)
    if not bot.blacklist:
        error = "No blacklist configured for article filtering"
        validation_errors.append(error)
        current_app.logger.debug(f"Validation failed: {error}")
    
    # Category and Slack validation
    if category:
        if not category.slack_channel:
            error = "Slack channel not configured in category"
            validation_errors.append(error)
            current_app.logger.debug(f"Validation failed: {error}")
    else:
        error = "Category not configured"
        validation_errors.append(error)
        current_app.logger.debug(f"Validation failed: {error}")

    if validation_errors:
        current_app.logger.debug(
            f"Bot '{bot.name}' validation failed with {len(validation_errors)} errors"
        )
    else:
        current_app.logger.debug(f"Bot '{bot.name}' passed all validation checks")
    
    return validation_errors
