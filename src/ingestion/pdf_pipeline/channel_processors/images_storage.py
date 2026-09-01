import mimetypes
import uuid
import aioboto3
import hashlib

class R2ImageStorage:
    def __init__(self, r2_config: dict):
        self.bucket_name = r2_config['bucket_name']
        self.endpoint_url = f"https://{r2_config['account_id']}.r2.cloudflarestorage.com"
        self.access_key_id = r2_config['access_key_id']
        self.secret_access_key = r2_config['secret_access_key']
        self.public_url = r2_config['r2_public_url'].rstrip('/')
        self.session = aioboto3.Session()

    async def upload_image(self, image: bytes, img_ext: str) -> str:
        ext = img_ext.lower().lstrip('.')
        content_type = mimetypes.guess_type(f"file.{ext}")[0] or f"image/{ext}"
        img_name = self.create_image_name(image, ext)

        async with self.session.client(  # type: ignore
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        ) as s3_client:

            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=img_name,
                Body=image,
                ContentType=content_type
            )

        return f"{self.public_url}/{img_name}"

    @classmethod
    def create_image_name(cls, img_bytes: bytes, img_ext: str):
        return f'img_{hashlib.sha256(img_bytes).hexdigest()}.{img_ext}'

    async def delete_images(self, delete_payload: dict):
        async with self.session.client(  # type: ignore
            service_name="s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key
        ) as s3_client:
            response = await s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete=delete_payload
            )
            return response
