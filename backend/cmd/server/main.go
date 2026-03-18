package main

import (
	"context"
	"log"
	"net/http"
	"os/signal"
	"syscall"

	"github.com/lebo/ai-video/backend/internal/platform/config"
	platformdb "github.com/lebo/ai-video/backend/internal/platform/db"
	platformhttp "github.com/lebo/ai-video/backend/internal/platform/http"
	"github.com/lebo/ai-video/backend/internal/platform/queue"
	"github.com/lebo/ai-video/backend/internal/platform/storage"
)

func main() {
	cfg := config.Load()
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	db, err := platformdb.New(ctx, cfg)
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	defer db.Close()

	if err := db.Migrate(ctx); err != nil {
		log.Fatalf("migrate db: %v", err)
	}

	redisQueue, err := queue.New(cfg)
	if err != nil {
		log.Fatalf("open redis: %v", err)
	}
	defer redisQueue.Close()

	objectStorage, err := storage.New(cfg)
	if err != nil {
		log.Fatalf("open storage: %v", err)
	}

	app := platformhttp.NewApp(cfg, db, redisQueue, objectStorage)
	go app.StartRenderWorker(ctx)

	server := &http.Server{
		Addr:    ":" + cfg.APIPort,
		Handler: app.Router(),
	}

	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()

	log.Printf("backend listening on :%s", cfg.APIPort)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("serve http: %v", err)
	}
}
