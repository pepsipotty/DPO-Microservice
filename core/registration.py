"""
Service registration with the gateway.

Handles registration/unregistration with the stable gateway endpoint,
including retry logic and lifecycle management.
"""

import asyncio
import logging
from typing import Optional
import time

import httpx
from .config import get_config

logger = logging.getLogger(__name__)


class ServiceRegistrar:
    """Handles service registration with the gateway."""
    
    def __init__(self):
        self.config = get_config()
        self.client: Optional[httpx.AsyncClient] = None
        self.registration_task: Optional[asyncio.Task] = None
        self.shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the registration process."""
        if not self.config.registration_enabled:
            logger.info("Service registration disabled (missing configuration)")
            return
            
        logger.info("Starting service registration")
        self.client = httpx.AsyncClient(timeout=10.0)
        
        # Register immediately
        await self._register()
        
        # Start background registration maintenance
        self.registration_task = asyncio.create_task(self._registration_loop())
    
    async def stop(self) -> None:
        """Stop registration and unregister service."""
        logger.info("Stopping service registration")
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Cancel background task
        if self.registration_task:
            self.registration_task.cancel()
            try:
                await self.registration_task
            except asyncio.CancelledError:
                pass
        
        # Unregister service
        if self.config.registration_enabled:
            await self._unregister()
        
        # Close client
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def _register(self) -> bool:
        """Register service with the gateway."""
        if not self.client:
            return False
            
        try:
            headers = {
                "X-DPO-Register-Secret": self.config.register_secret,
                "Content-Type": "application/json"
            }
            
            payload = {
                "base_url": self.config.public_base_url.rstrip("/"),
                "version": "1.0.0",  # Could be made configurable
                "ttl_seconds": self.config.service_ttl_seconds
            }
            
            logger.info(f"Registering service with gateway: {self.config.register_url}")
            
            response = await self.client.post(
                self.config.register_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code in (200, 201, 204):
                logger.info("Service registration successful")
                return True
            else:
                logger.error(f"Registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False
    
    async def _unregister(self) -> None:
        """Unregister service from the gateway."""
        if not self.client:
            return
            
        try:
            headers = {
                "X-DPO-Register-Secret": self.config.register_secret
            }
            
            logger.info("Unregistering service from gateway")
            
            response = await self.client.delete(
                self.config.register_url,
                headers=headers
            )
            
            if response.status_code in (200, 204, 404):
                logger.info("Service unregistration successful")
            else:
                logger.warning(f"Unregistration failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.warning(f"Unregistration error: {e}")
    
    async def _registration_loop(self) -> None:
        """Background loop to maintain registration."""
        retry_delay = 30  # Start with 30 second delay
        max_retry_delay = 300  # Max 5 minutes
        
        while not self.shutdown_event.is_set():
            try:
                # Wait for renewal time (3/4 of TTL)
                renewal_delay = self.config.service_ttl_seconds * 0.75
                
                await asyncio.wait_for(
                    self.shutdown_event.wait(), 
                    timeout=renewal_delay
                )
                
                # If we reach here, shutdown was signaled
                break
                
            except asyncio.TimeoutError:
                # Time to renew registration
                logger.debug("Renewing service registration")
                
                if await self._register():
                    # Success - reset retry delay
                    retry_delay = 30
                else:
                    # Failed - exponential backoff
                    logger.warning(f"Registration renewal failed, retrying in {retry_delay}s")
                    
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(), 
                            timeout=retry_delay
                        )
                        break  # Shutdown signaled during retry wait
                    except asyncio.TimeoutError:
                        # Continue retry loop
                        pass
                    
                    retry_delay = min(retry_delay * 2, max_retry_delay)


# Global registrar instance
_registrar: Optional[ServiceRegistrar] = None


def get_registrar() -> ServiceRegistrar:
    """Get the global service registrar instance."""
    global _registrar
    if _registrar is None:
        _registrar = ServiceRegistrar()
    return _registrar


async def start_registration() -> None:
    """Start service registration."""
    registrar = get_registrar()
    await registrar.start()


async def stop_registration() -> None:
    """Stop service registration."""
    registrar = get_registrar()
    await registrar.stop()