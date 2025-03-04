import os
from typing import List, Dict, Any, Optional, BinaryIO
from minio import Minio
from minio.error import S3Error

class MinioService:
    """Service for interacting with MinIO object storage"""
    
    def __init__(self):
        """Initialize MinIO client using environment variables"""
        host = os.environ.get('MINIO_HOST', 'localhost:9000')
        access_key = os.environ.get('MINIO_KEY_ID')
        secret_key = os.environ.get('MINIO_SECRET_KEY')
        
        if not access_key or not secret_key:
            raise ValueError("MinIO credentials not found in environment variables")
        
        secure = host.startswith('https://') or not host.startswith('http://')
        
        # Remove protocol prefix if present
        if host.startswith('http://'):
            host = host[7:]
        elif host.startswith('https://'):
            host = host[8:]
        
        self.client = Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
    
    def list_objects(self, bucket_name: str, prefix: str = None) -> List[Dict[str, Any]]:
        """
        List objects in a bucket
        
        Args:
            bucket_name: Name of the bucket
            prefix: Optional prefix to filter objects
            
        Returns:
            List of objects with their metadata
        """
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            return [
                {
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified
                }
                for obj in objects
            ]
        except S3Error as e:
            raise Exception(f"Error listing objects: {e}")
    
    def put_object(self, bucket_name: str, object_name: str, data: BinaryIO, length: int, content_type: str = 'application/octet-stream') -> Dict[str, Any]:
        """
        Upload an object to a bucket
        
        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            data: Binary data to upload
            length: Size of the data in bytes
            content_type: MIME type of the object
            
        Returns:
            Dictionary with etag and other metadata
        """
        try:
            result = self.client.put_object(
                bucket_name,
                object_name,
                data,
                length,
                content_type=content_type
            )
            return {
                'etag': result.etag,
                'version_id': result.version_id
            }
        except S3Error as e:
            raise Exception(f"Error uploading object: {e}")
    
    def get_object(self, bucket_name: str, object_name: str) -> BinaryIO:
        """
        Get an object from a bucket
        
        Args:
            bucket_name: Name of the bucket
            object_name: Name of the object
            
        Returns:
            Binary data of the object
        """
        try:
            return self.client.get_object(bucket_name, object_name)
        except S3Error as e:
            raise Exception(f"Error retrieving object: {e}")
    
    def create_bucket_if_not_exists(self, bucket_name: str, location: str = "us-east-1") -> bool:
        """
        Create a bucket if it doesn't exist
        
        Args:
            bucket_name: Name of the bucket
            location: Region for the bucket
            
        Returns:
            True if bucket was created, False if it already existed
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name, location=location)
                return True
            return False
        except S3Error as e:
            raise Exception(f"Error creating bucket: {e}")
