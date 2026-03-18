package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	AppEnv               string
	APIPort              string
	AIServiceBaseURL     string
	PostgresDSN          string
	RedisAddr            string
	RedisPassword        string
	GenerationStream     string
	RenderStream         string
	MaxParallelTasks     int
	MinioEndpoint        string
	MinioAccessKey       string
	MinioSecretKey       string
	MinioBucket          string
	MinioUseSSL          bool
	MinioPublicBaseURL   string
	SignedURLTTL         time.Duration
	DefaultAspectRatio   string
	ShutdownTimeout      time.Duration
	RenderPollInterval   time.Duration
}

func Load() Config {
	return Config{
		AppEnv:             getenv("APP_ENV", "development"),
		APIPort:            getenv("API_PORT", "8080"),
		AIServiceBaseURL:   getenv("AI_SERVICE_BASE_URL", "http://localhost:8000"),
		PostgresDSN:        buildPostgresDSN(),
		RedisAddr:          getenv("REDIS_ADDR", "localhost:6379"),
		RedisPassword:      os.Getenv("REDIS_PASSWORD"),
		GenerationStream:   getenv("QUEUE_STREAM_GENERATION", "stream.generation"),
		RenderStream:       getenv("QUEUE_STREAM_RENDER", "stream.render"),
		MaxParallelTasks:   getenvInt("MAX_PARALLEL_VIDEO_TASKS", 3),
		MinioEndpoint:      getenv("MINIO_ENDPOINT", "localhost:9000"),
		MinioAccessKey:     getenv("MINIO_ACCESS_KEY", "minioadmin"),
		MinioSecretKey:     getenv("MINIO_SECRET_KEY", "minioadmin"),
		MinioBucket:        getenv("MINIO_BUCKET", "ai-video"),
		MinioUseSSL:        getenvBool("MINIO_USE_SSL", false),
		MinioPublicBaseURL: getenv("MINIO_PUBLIC_BASE_URL", "http://localhost:9000"),
		SignedURLTTL:       time.Duration(getenvInt("SIGNED_URL_TTL_SECONDS", 3600)) * time.Second,
		DefaultAspectRatio: getenv("DEFAULT_ASPECT_RATIO", "9:16"),
		ShutdownTimeout:    10 * time.Second,
		RenderPollInterval: 5 * time.Second,
	}
}

func buildPostgresDSN() string {
	if dsn := os.Getenv("POSTGRES_DSN"); dsn != "" {
		return dsn
	}
	host := getenv("POSTGRES_HOST", "localhost")
	port := getenv("POSTGRES_PORT", "5432")
	user := getenv("POSTGRES_USER", "postgres")
	password := getenv("POSTGRES_PASSWORD", "postgres")
	db := getenv("POSTGRES_DB", "ai_video")
	sslMode := getenv("POSTGRES_SSLMODE", "disable")
	return "postgres://" + user + ":" + password + "@" + host + ":" + port + "/" + db + "?sslmode=" + sslMode
}

func getenv(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func getenvInt(key string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func getenvBool(key string, fallback bool) bool {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return fallback
	}
	return parsed
}
