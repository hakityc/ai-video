package storage

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"net/url"
	"path"
	"strings"
	"time"

	"github.com/lebo/ai-video/backend/internal/platform/config"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type ObjectStorage struct {
	client *minio.Client
	cfg    config.Config
}

type UploadResult struct {
	Bucket    string `json:"bucket"`
	ObjectKey string `json:"object_key"`
	URL       string `json:"url"`
}

func New(cfg config.Config) (*ObjectStorage, error) {
	client, err := minio.New(cfg.MinioEndpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(cfg.MinioAccessKey, cfg.MinioSecretKey, ""),
		Secure: cfg.MinioUseSSL,
	})
	if err != nil {
		return nil, fmt.Errorf("new minio client: %w", err)
	}
	return &ObjectStorage{client: client, cfg: cfg}, nil
}

func (s *ObjectStorage) UploadBytes(ctx context.Context, objectKey string, data []byte, contentType string) (*UploadResult, error) {
	reader := bytes.NewReader(data)
	_, err := s.client.PutObject(ctx, s.cfg.MinioBucket, objectKey, reader, int64(len(data)), minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return nil, fmt.Errorf("put object: %w", err)
	}
	return &UploadResult{
		Bucket:    s.cfg.MinioBucket,
		ObjectKey: objectKey,
		URL:       s.PublicURL(objectKey),
	}, nil
}

func (s *ObjectStorage) UploadReader(ctx context.Context, objectKey string, reader io.Reader, size int64, contentType string) (*UploadResult, error) {
	_, err := s.client.PutObject(ctx, s.cfg.MinioBucket, objectKey, reader, size, minio.PutObjectOptions{
		ContentType: contentType,
	})
	if err != nil {
		return nil, fmt.Errorf("put object: %w", err)
	}
	return &UploadResult{
		Bucket:    s.cfg.MinioBucket,
		ObjectKey: objectKey,
		URL:       s.PublicURL(objectKey),
	}, nil
}

func (s *ObjectStorage) SignedGetURL(ctx context.Context, objectKey string) (string, error) {
	reqParams := make(url.Values)
	presignedURL, err := s.client.PresignedGetObject(ctx, s.cfg.MinioBucket, objectKey, s.cfg.SignedURLTTL, reqParams)
	if err != nil {
		return "", fmt.Errorf("presign object: %w", err)
	}
	return presignedURL.String(), nil
}

func (s *ObjectStorage) PublicURL(objectKey string) string {
	base := strings.TrimRight(s.cfg.MinioPublicBaseURL, "/")
	return base + "/" + path.Join(s.cfg.MinioBucket, objectKey)
}

func (s *ObjectStorage) DownloadToBuffer(ctx context.Context, objectKey string) ([]byte, error) {
	reader, err := s.client.GetObject(ctx, s.cfg.MinioBucket, objectKey, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("get object: %w", err)
	}
	defer reader.Close()
	return io.ReadAll(reader)
}

func (s *ObjectStorage) Exists(ctx context.Context, objectKey string) (bool, error) {
	_, err := s.client.StatObject(ctx, s.cfg.MinioBucket, objectKey, minio.StatObjectOptions{})
	if err == nil {
		return true, nil
	}
	if minio.ToErrorResponse(err).Code == "NoSuchKey" {
		return false, nil
	}
	return false, err
}

func TimestampedObjectKey(prefix, filename string) string {
	stamp := time.Now().UTC().Format("20060102T150405")
	filename = strings.ReplaceAll(filename, " ", "-")
	return path.Join(prefix, stamp+"-"+filename)
}
