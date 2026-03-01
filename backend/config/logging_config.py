"""
Structured JSON logging configuration for production
"""
import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add level
        log_record['level'] = record.levelname
        
        # Add function and line number for debugging
        log_record['function'] = record.funcName
        log_record['line'] = record.lineno
        
        # Add module
        log_record['module'] = record.module
        
        # Add process and thread info for async debugging
        log_record['process_id'] = record.process
        log_record['thread_name'] = record.threadName


def setup_logging(log_file: str = "logs/app.log", log_level: str = "INFO"):
    """
    Setup structured JSON logging
    
    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'standard': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'formatter': 'json',
                'maxBytes': 10485760,  # 10 MB
                'backupCount': 5,
                'level': log_level
            },
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
                'level': log_level
            }
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['file', 'console'],
                'level': log_level,
                'propagate': True
            },
            'fastapi': {
                'handlers': ['file', 'console'],
                'level': log_level,
                'propagate': False
            },
            'sqlalchemy': {
                'handlers': ['file', 'console'],
                'level': 'WARNING',
                'propagate': False
            },
            'uvicorn': {
                'handlers': ['file', 'console'],
                'level': log_level,
                'propagate': False
            }
        }
    }
    
    logging.config.dictConfig(config)
    
    # Return root logger
    return logging.getLogger()


# Get logger function for modules
def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module"""
    return logging.getLogger(name)
