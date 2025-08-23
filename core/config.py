"""
Configuration management for the DPO microservice.

Handles environment variables and provides typed configuration access
for gateway integration and service settings.
"""

import os
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ServiceConfig:
    """Configuration for the DPO microservice."""
    
    # Gateway integration settings
    public_base_url: Optional[str]
    register_url: Optional[str] 
    register_secret: Optional[str]
    gateway_shared_secret: str
    service_ttl_seconds: int
    
    # CORS and security
    allow_direct_origins: List[str]
    
    # Service settings
    max_concurrent_jobs: int
    job_timeout_seconds: int
    max_dataset_size_mb: int
    rate_limit_per_minute: int
    
    # Storage and paths
    working_directory: str
    cache_directory: str
    
    @classmethod
    def from_environment(cls) -> "ServiceConfig":
        """Load configuration from environment variables."""
        
        # Parse direct origins
        direct_origins = []
        origins_env = os.getenv("DPO_ALLOW_DIRECT_ORIGINS", "")
        if origins_env:
            direct_origins = [origin.strip() for origin in origins_env.split(",")]
        
        return cls(
            # Gateway integration
            public_base_url=os.getenv("DPO_PUBLIC_BASE_URL"),
            register_url=os.getenv("DPO_REGISTER_URL"),
            register_secret=os.getenv("DPO_REGISTER_SECRET"),
            gateway_shared_secret=os.getenv("DPO_GATEWAY_SHARED_SECRET", ""),
            service_ttl_seconds=int(os.getenv("DPO_SERVICE_TTL_SECONDS", "21600")),  # 6 hours
            
            # CORS and security
            allow_direct_origins=direct_origins,
            
            # Service limits
            max_concurrent_jobs=int(os.getenv("DPO_MAX_CONCURRENT_JOBS", "2")),
            job_timeout_seconds=int(os.getenv("DPO_JOB_TIMEOUT_SECONDS", "3600")),  # 1 hour
            max_dataset_size_mb=int(os.getenv("DPO_MAX_DATASET_SIZE_MB", "5")),
            rate_limit_per_minute=int(os.getenv("DPO_RATE_LIMIT_PER_MINUTE", "5")),
            
            # Paths
            working_directory=os.getenv("DPO_WORKING_DIR", "/app"),
            cache_directory=os.getenv("DPO_CACHE_DIR", "/app/.cache"),
        )
    
    def validate(self) -> None:
        """Validate configuration and raise errors for critical missing values."""
        if not self.gateway_shared_secret:
            raise ValueError("DPO_GATEWAY_SHARED_SECRET is required for HMAC verification")
            
        if self.public_base_url and self.register_url and not self.register_secret:
            raise ValueError("DPO_REGISTER_SECRET is required when registration is enabled")
    
    @property
    def registration_enabled(self) -> bool:
        """Check if service registration is enabled."""
        return bool(
            self.public_base_url and 
            self.register_url and 
            self.register_secret
        )


# Global configuration instance
config: Optional[ServiceConfig] = None


def get_config() -> ServiceConfig:
    """Get the global configuration instance, loading from environment if needed."""
    global config
    if config is None:
        config = ServiceConfig.from_environment()
        config.validate()
    return config


def reload_config() -> ServiceConfig:
    """Force reload configuration from environment."""
    global config
    config = ServiceConfig.from_environment() 
    config.validate()
    return config