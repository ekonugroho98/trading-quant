"""
Logging System Module
Structured logging dengan levels, rotation, dan JSON format support
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sys


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter untuk structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


class TradingLogger:
    """Centralized logging system untuk trading quant"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _initialized = False
    
    @classmethod
    def get_logger(cls, name: str = 'trading_quant', 
                   log_level: str = 'INFO',
                   log_to_file: bool = True,
                   log_to_console: bool = True,
                   log_dir: str = 'logs') -> logging.Logger:
        """
        Get or create logger instance
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Enable file logging
            log_to_console: Enable console logging
            log_dir: Directory untuk log files
        
        Returns:
            Logger instance
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.handlers.clear()  # Clear existing handlers
        
        # Prevent duplicate logs
        logger.propagate = False
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler dengan rotation
        if log_to_file:
            # Create log directory
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)
            
            # Rotating file handler (10MB per file, keep 5 backups)
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_path / f'{name}.log',
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # File logs semua level
            
            # JSON formatter untuk file
            json_formatter = JSONFormatter()
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)
            
            # Error log file (hanya ERROR dan CRITICAL)
            error_handler = logging.handlers.RotatingFileHandler(
                filename=log_path / f'{name}_errors.log',
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            logger.addHandler(error_handler)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def log_with_context(cls, logger: logging.Logger, level: str, message: str, 
                        **kwargs) -> None:
        """
        Log dengan additional context fields
        
        Args:
            logger: Logger instance
            level: Log level
            message: Log message
            **kwargs: Additional context fields
        """
        extra = {'extra_fields': kwargs}
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, extra=extra)


# Default logger instance
def get_logger(name: str = 'trading_quant', **kwargs) -> logging.Logger:
    """Get default logger instance"""
    return TradingLogger.get_logger(name, **kwargs)


# Convenience functions
def log_debug(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log debug message dengan context"""
    TradingLogger.log_with_context(logger, 'DEBUG', message, **kwargs)


def log_info(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log info message dengan context"""
    TradingLogger.log_with_context(logger, 'INFO', message, **kwargs)


def log_warning(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log warning message dengan context"""
    TradingLogger.log_with_context(logger, 'WARNING', message, **kwargs)


def log_error(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log error message dengan context"""
    TradingLogger.log_with_context(logger, 'ERROR', message, **kwargs)


def log_critical(logger: logging.Logger, message: str, **kwargs) -> None:
    """Log critical message dengan context"""
    TradingLogger.log_with_context(logger, 'CRITICAL', message, **kwargs)

