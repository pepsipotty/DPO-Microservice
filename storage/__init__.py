"""
Storage interface abstractions for DPO Microservice.

This module defines the interface contracts for different storage backends,
ensuring consistency across Firebase, local file system, and other storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, BinaryIO
from pathlib import Path
import os
import json
import firebase_admin
from firebase_admin import credentials, storage as firebase_storage


class StorageInterface(ABC):
    """
    Abstract interface for storage backends used in the DPO microservice.
    
    All storage implementations must implement this interface to ensure
    compatibility with the training and serving pipeline.
    """
    
    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Upload a file to the storage backend.
        
        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path in the storage backend
            metadata: Optional metadata to attach to the file
            
        Returns:
            URL or identifier for the uploaded file
            
        Raises:
            StorageError: If upload fails
        """
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from the storage backend.
        
        Args:
            remote_path: Path to the file in the storage backend
            local_path: Local destination path
            
        Returns:
            True if download was successful
            
        Raises:
            StorageError: If download fails
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from the storage backend.
        
        Args:
            remote_path: Path to the file in the storage backend
            
        Returns:
            True if deletion was successful
            
        Raises:
            StorageError: If deletion fails
        """
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in the storage backend.
        
        Args:
            remote_path: Path to check in the storage backend
            
        Returns:
            True if file exists
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in the storage backend with optional prefix filtering.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths
        """
        pass
    
    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the type of storage backend."""
        pass


class StorageError(Exception):
    """Raised when storage operations fail."""
    pass


class FirebaseStorage(StorageInterface):
    """
    Firebase Storage implementation for file storage and retrieval.
    
    This implementation provides integration with Firebase Storage for
    storing training artifacts, models, and datasets.
    """
    
    def __init__(self, bucket_name: str, service_key_path: Optional[str] = None):
        """
        Initialize Firebase Storage.
        
        Args:
            bucket_name: Name of the Firebase Storage bucket
            service_key_path: Path to Firebase service account key file
        """
        self.bucket_name = bucket_name
        self.service_key_path = service_key_path
        self._bucket = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase app and storage bucket."""
        try:
            # Check if Firebase app is already initialized
            try:
                app = firebase_admin.get_app()
            except ValueError:
                # Initialize Firebase app
                if self.service_key_path and os.path.exists(self.service_key_path):
                    cred = credentials.Certificate(self.service_key_path)
                    firebase_admin.initialize_app(cred, {
                        "storageBucket": self.bucket_name
                    })
                else:
                    raise StorageError(f"Firebase service key not found: {self.service_key_path}")
            
            # Get storage bucket
            self._bucket = firebase_storage.bucket(self.bucket_name)
            
        except Exception as e:
            raise StorageError(f"Failed to initialize Firebase Storage: {e}")
    
    @property
    def backend_type(self) -> str:
        """Return the type of storage backend."""
        return "firebase"
    
    def upload_file(self, local_path: str, remote_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Upload a file to Firebase Storage.
        
        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path in Firebase Storage
            metadata: Optional metadata to attach to the file
            
        Returns:
            Download URL for the uploaded file
            
        Raises:
            StorageError: If upload fails
        """
        try:
            if not os.path.exists(local_path):
                raise StorageError(f"Local file not found: {local_path}")
            
            blob = self._bucket.blob(remote_path)
            
            # Set metadata if provided
            if metadata:
                blob.metadata = metadata
            
            # Upload file
            blob.upload_from_filename(local_path)
            
            # Make file publicly accessible and return download URL
            blob.make_public()
            return blob.public_url
            
        except Exception as e:
            raise StorageError(f"Failed to upload file {local_path} to {remote_path}: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from Firebase Storage.
        
        Args:
            remote_path: Path to the file in Firebase Storage
            local_path: Local destination path
            
        Returns:
            True if download was successful
            
        Raises:
            StorageError: If download fails
        """
        try:
            blob = self._bucket.blob(remote_path)
            
            if not blob.exists():
                raise StorageError(f"File not found in Firebase Storage: {remote_path}")
            
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            blob.download_to_filename(local_path)
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to download file {remote_path} to {local_path}: {e}")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from Firebase Storage.
        
        Args:
            remote_path: Path to the file in Firebase Storage
            
        Returns:
            True if deletion was successful
            
        Raises:
            StorageError: If deletion fails
        """
        try:
            blob = self._bucket.blob(remote_path)
            
            if not blob.exists():
                return True  # File doesn't exist, consider it deleted
            
            blob.delete()
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete file {remote_path}: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in Firebase Storage.
        
        Args:
            remote_path: Path to check in Firebase Storage
            
        Returns:
            True if file exists
        """
        try:
            blob = self._bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in Firebase Storage with optional prefix filtering.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of file paths
        """
        try:
            blobs = self._bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise StorageError(f"Failed to list files with prefix '{prefix}': {e}")


class LocalFileStorage(StorageInterface):
    """
    Local file system storage implementation.
    
    This implementation provides file operations on the local file system,
    useful for development and testing.
    """
    
    def __init__(self, base_path: str = ".cache"):
        """
        Initialize local file storage.
        
        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def backend_type(self) -> str:
        """Return the type of storage backend."""
        return "local"
    
    def _get_full_path(self, remote_path: str) -> Path:
        """Get full local path for a given remote path."""
        return self.base_path / remote_path
    
    def upload_file(self, local_path: str, remote_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Copy a file to the local storage directory.
        
        Args:
            local_path: Path to the local file to copy
            remote_path: Destination path in local storage
            metadata: Optional metadata (stored as JSON sidecar file)
            
        Returns:
            Full path to the stored file
            
        Raises:
            StorageError: If copy fails
        """
        try:
            if not os.path.exists(local_path):
                raise StorageError(f"Local file not found: {local_path}")
            
            full_path = self._get_full_path(remote_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(local_path, full_path)
            
            # Store metadata if provided
            if metadata:
                metadata_path = full_path.with_suffix(full_path.suffix + ".metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            return str(full_path)
            
        except Exception as e:
            raise StorageError(f"Failed to upload file {local_path} to {remote_path}: {e}")
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Copy a file from local storage to another local path.
        
        Args:
            remote_path: Path to the file in local storage
            local_path: Local destination path
            
        Returns:
            True if copy was successful
            
        Raises:
            StorageError: If copy fails
        """
        try:
            full_path = self._get_full_path(remote_path)
            
            if not full_path.exists():
                raise StorageError(f"File not found in local storage: {remote_path}")
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Copy file
            import shutil
            shutil.copy2(full_path, local_path)
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to download file {remote_path} to {local_path}: {e}")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from local storage.
        
        Args:
            remote_path: Path to the file in local storage
            
        Returns:
            True if deletion was successful
            
        Raises:
            StorageError: If deletion fails
        """
        try:
            full_path = self._get_full_path(remote_path)
            
            if not full_path.exists():
                return True  # File doesn't exist, consider it deleted
            
            full_path.unlink()
            
            # Also delete metadata file if it exists
            metadata_path = full_path.with_suffix(full_path.suffix + ".metadata.json")
            if metadata_path.exists():
                metadata_path.unlink()
            
            return True
            
        except Exception as e:
            raise StorageError(f"Failed to delete file {remote_path}: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in local storage.
        
        Args:
            remote_path: Path to check in local storage
            
        Returns:
            True if file exists
        """
        full_path = self._get_full_path(remote_path)
        return full_path.exists()
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in local storage with optional prefix filtering.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of relative file paths
        """
        try:
            files = []
            search_path = self.base_path / prefix if prefix else self.base_path
            
            if search_path.is_dir():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file() and not file_path.name.endswith(".metadata.json"):
                        relative_path = file_path.relative_to(self.base_path)
                        files.append(str(relative_path))
            
            return sorted(files)
            
        except Exception as e:
            raise StorageError(f"Failed to list files with prefix '{prefix}': {e}")


# Storage factory
def create_storage(storage_type: str = "firebase", **kwargs) -> StorageInterface:
    """
    Create a storage backend instance.
    
    Args:
        storage_type: Type of storage backend ("firebase" or "local")
        **kwargs: Arguments to pass to the storage constructor
        
    Returns:
        Storage backend instance
        
    Raises:
        ValueError: If storage type is not supported
    """
    if storage_type == "firebase":
        return FirebaseStorage(**kwargs)
    elif storage_type == "local":
        return LocalFileStorage(**kwargs)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


# Export the interface and implementations
__all__ = [
    "StorageInterface",
    "StorageError",
    "FirebaseStorage",
    "LocalFileStorage",
    "create_storage"
]