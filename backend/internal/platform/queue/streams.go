package queue

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/lebo/ai-video/backend/internal/platform/config"
	"github.com/redis/go-redis/v9"
)

const (
	GenerationConsumerGroup = "generation-workers"
	RenderConsumerGroup     = "render-workers"
)

type Queue struct {
	client *redis.Client
	cfg    config.Config
}

type JobMessage struct {
	ID      string         `json:"id"`
	Kind    string         `json:"kind"`
	Payload map[string]any `json:"payload"`
}

func New(cfg config.Config) (*Queue, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
	})
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("ping redis: %w", err)
	}
	queue := &Queue{client: client, cfg: cfg}
	if err := queue.ensureStreamGroups(ctx); err != nil {
		return nil, err
	}
	return queue, nil
}

func (q *Queue) Close() error {
	return q.client.Close()
}

func (q *Queue) ensureStreamGroups(ctx context.Context) error {
	if err := q.client.XGroupCreateMkStream(ctx, q.cfg.GenerationStream, GenerationConsumerGroup, "$").Err(); err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		return fmt.Errorf("create generation group: %w", err)
	}
	if err := q.client.XGroupCreateMkStream(ctx, q.cfg.RenderStream, RenderConsumerGroup, "$").Err(); err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
		return fmt.Errorf("create render group: %w", err)
	}
	return nil
}

func (q *Queue) Publish(ctx context.Context, stream string, message JobMessage) error {
	payload, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("marshal job message: %w", err)
	}
	return q.client.XAdd(ctx, &redis.XAddArgs{
		Stream: stream,
		Values: map[string]any{
			"message": string(payload),
		},
	}).Err()
}

func (q *Queue) Consume(ctx context.Context, stream, group, consumer string, block time.Duration, count int64) ([]redis.XMessage, error) {
	streams, err := q.client.XReadGroup(ctx, &redis.XReadGroupArgs{
		Group:    group,
		Consumer: consumer,
		Streams:  []string{stream, ">"},
		Count:    count,
		Block:    block,
		NoAck:    false,
	}).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if len(streams) == 0 {
		return nil, nil
	}
	return streams[0].Messages, nil
}

func (q *Queue) Ack(ctx context.Context, stream, group string, ids ...string) error {
	if len(ids) == 0 {
		return nil
	}
	return q.client.XAck(ctx, stream, group, ids...).Err()
}
