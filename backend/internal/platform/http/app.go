package http

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	stdhttp "net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/lebo/ai-video/backend/internal/platform/config"
	platformdb "github.com/lebo/ai-video/backend/internal/platform/db"
	"github.com/lebo/ai-video/backend/internal/platform/queue"
	"github.com/lebo/ai-video/backend/internal/platform/storage"
)

type App struct {
	cfg     config.Config
	db      *platformdb.DB
	queue   *queue.Queue
	storage *storage.ObjectStorage
	client  *stdhttp.Client
}

type projectRecord struct {
	ID             uuid.UUID  `json:"id"`
	Name           string     `json:"name"`
	Genre          string     `json:"genre"`
	Style          string     `json:"style"`
	AspectRatio    string     `json:"aspect_ratio"`
	TargetDuration int        `json:"target_duration"`
	Status         string     `json:"status"`
	CreatedBy      *string    `json:"created_by,omitempty"`
	CreatedAt      time.Time  `json:"created_at"`
	UpdatedAt      time.Time  `json:"updated_at"`
	Episodes       []any      `json:"episodes,omitempty"`
	Characters     []any      `json:"characters,omitempty"`
	Locations      []any      `json:"locations,omitempty"`
}

type assetReference struct {
	AssetID string `json:"asset_id,omitempty"`
	URL     string `json:"url"`
	Label   string `json:"label,omitempty"`
}

type characterRecord struct {
	ID              uuid.UUID        `json:"id"`
	ProjectID       uuid.UUID        `json:"project_id"`
	Name            string           `json:"name"`
	AgeTag          string           `json:"age_tag"`
	AppearanceDesc  string           `json:"appearance_desc"`
	PersonalityDesc string           `json:"personality_desc"`
	SpeakingStyle   string           `json:"speaking_style"`
	CostumeDesc     string           `json:"costume_desc"`
	LockedAttributes []string        `json:"locked_attributes"`
	ReferenceAssets []assetReference `json:"reference_assets"`
	CreatedAt       time.Time        `json:"created_at"`
	UpdatedAt       time.Time        `json:"updated_at"`
}

type locationRecord struct {
	ID              uuid.UUID        `json:"id"`
	ProjectID       uuid.UUID        `json:"project_id"`
	Name            string           `json:"name"`
	Description     string           `json:"description"`
	StyleTags       []string         `json:"style_tags"`
	ReferenceAssets []assetReference `json:"reference_assets"`
	CreatedAt       time.Time        `json:"created_at"`
	UpdatedAt       time.Time        `json:"updated_at"`
}

type storyCardRecord struct {
	ID         uuid.UUID       `json:"id"`
	EpisodeID  uuid.UUID       `json:"episode_id"`
	Theme      string          `json:"theme"`
	Conflict   string          `json:"conflict"`
	Twist      string          `json:"twist"`
	EndingHook string          `json:"ending_hook"`
	Summary    string          `json:"summary"`
	RawPayload json.RawMessage `json:"raw_payload"`
	CreatedAt  time.Time       `json:"created_at"`
	UpdatedAt  time.Time       `json:"updated_at"`
}

type sceneRecord struct {
	ID                  uuid.UUID `json:"id"`
	EpisodeID           uuid.UUID `json:"episode_id"`
	OrderNo             int       `json:"order_no"`
	Summary             string    `json:"summary"`
	InvolvedCharacterIDs []string `json:"involved_character_ids"`
	InvolvedLocationIDs []string  `json:"involved_location_ids"`
	CreatedAt           time.Time `json:"created_at"`
	UpdatedAt           time.Time `json:"updated_at"`
}

type shotRecord struct {
	ID              uuid.UUID `json:"id"`
	EpisodeID       uuid.UUID `json:"episode_id"`
	SceneID         *uuid.UUID `json:"scene_id,omitempty"`
	OrderNo         int       `json:"order_no"`
	Duration        int       `json:"duration"`
	Description     string    `json:"description"`
	ShotType        string    `json:"shot_type"`
	CameraMotion    string    `json:"camera_motion"`
	SubjectDesc     string    `json:"subject_desc"`
	ActionDesc      string    `json:"action_desc"`
	EmotionDesc     string    `json:"emotion_desc"`
	DialogueText    string    `json:"dialogue_text"`
	GenerationMode  string    `json:"generation_mode"`
	Status          string    `json:"status"`
	CurrentVersionID *uuid.UUID `json:"current_version_id,omitempty"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
	Versions        []any     `json:"versions,omitempty"`
}

type shotVersionRecord struct {
	ID           uuid.UUID       `json:"id"`
	ShotID       uuid.UUID       `json:"shot_id"`
	TaskID       uuid.UUID       `json:"task_id"`
	AssetID      uuid.UUID       `json:"asset_id"`
	Provider     string          `json:"provider"`
	Model        string          `json:"model"`
	IsSelected   bool            `json:"is_selected"`
	PromptPayload json.RawMessage `json:"prompt_payload"`
	Metadata     json.RawMessage `json:"metadata"`
	CreatedAt    time.Time       `json:"created_at"`
	AssetURL     string          `json:"asset_url"`
}

type episodeRecord struct {
	ID             uuid.UUID         `json:"id"`
	ProjectID      uuid.UUID         `json:"project_id"`
	Title          string            `json:"title"`
	Logline        string            `json:"logline"`
	TargetDuration int               `json:"target_duration"`
	Status         string            `json:"status"`
	ExportStatus   string            `json:"export_status"`
	CreatedAt      time.Time         `json:"created_at"`
	UpdatedAt      time.Time         `json:"updated_at"`
	StoryCard      *storyCardRecord  `json:"story_card,omitempty"`
	Scenes         []sceneRecord     `json:"scenes,omitempty"`
	Shots          []shotRecord      `json:"shots,omitempty"`
	RenderJobs     []renderJobRecord `json:"render_jobs,omitempty"`
}

type assetRecord struct {
	ID        uuid.UUID       `json:"id"`
	ProjectID *uuid.UUID      `json:"project_id,omitempty"`
	Kind      string          `json:"kind"`
	Bucket    string          `json:"bucket"`
	ObjectKey string          `json:"object_key"`
	URL       string          `json:"url"`
	Metadata  json.RawMessage `json:"metadata"`
	CreatedAt time.Time       `json:"created_at"`
}

type taskRecord struct {
	ID           uuid.UUID       `json:"id"`
	ShotID       uuid.UUID       `json:"shot_id"`
	Provider     string          `json:"provider"`
	Model        string          `json:"model"`
	InputType    string          `json:"input_type"`
	CandidateIndex int          `json:"candidate_index"`
	PromptPayload json.RawMessage `json:"prompt_payload"`
	Status       string          `json:"status"`
	RawPayload   json.RawMessage `json:"raw_payload"`
	OutputAssetID *uuid.UUID      `json:"output_asset_id,omitempty"`
	ErrorMessage *string         `json:"error_message,omitempty"`
	CreatedAt    time.Time       `json:"created_at"`
	StartedAt    *time.Time      `json:"started_at,omitempty"`
	CompletedAt  *time.Time      `json:"completed_at,omitempty"`
	UpdatedAt    time.Time       `json:"updated_at"`
}

type renderJobRecord struct {
	ID                     uuid.UUID       `json:"id"`
	EpisodeID              uuid.UUID       `json:"episode_id"`
	SelectedShotVersionIDs []string        `json:"selected_shot_version_ids"`
	SubtitleAssetID        *uuid.UUID      `json:"subtitle_asset_id,omitempty"`
	VoiceAssetID           *uuid.UUID      `json:"voice_asset_id,omitempty"`
	BGMAssetID             *uuid.UUID      `json:"bgm_asset_id,omitempty"`
	OutputAssetID          *uuid.UUID      `json:"output_asset_id,omitempty"`
	Status                 string          `json:"status"`
	Metadata               json.RawMessage `json:"metadata"`
	ErrorMessage           *string         `json:"error_message,omitempty"`
	CreatedAt              time.Time       `json:"created_at"`
	UpdatedAt              time.Time       `json:"updated_at"`
	OutputURL              *string         `json:"output_url,omitempty"`
}

type createProjectRequest struct {
	Name           string  `json:"name" binding:"required"`
	Genre          string  `json:"genre" binding:"required"`
	Style          string  `json:"style" binding:"required"`
	AspectRatio    string  `json:"aspect_ratio"`
	TargetDuration int     `json:"target_duration" binding:"required"`
	CreatedBy      *string `json:"created_by"`
}

type createEpisodeRequest struct {
	Title          string `json:"title" binding:"required"`
	Logline        string `json:"logline" binding:"required"`
	TargetDuration int    `json:"target_duration" binding:"required"`
}

type createCharacterRequest struct {
	Name            string           `json:"name" binding:"required"`
	AgeTag          string           `json:"age_tag"`
	AppearanceDesc  string           `json:"appearance_desc" binding:"required"`
	PersonalityDesc string           `json:"personality_desc" binding:"required"`
	SpeakingStyle   string           `json:"speaking_style"`
	CostumeDesc     string           `json:"costume_desc" binding:"required"`
	LockedAttributes []string        `json:"locked_attributes"`
	ReferenceAssets []assetReference `json:"reference_assets"`
}

type createLocationRequest struct {
	Name            string           `json:"name" binding:"required"`
	Description     string           `json:"description" binding:"required"`
	StyleTags       []string         `json:"style_tags"`
	ReferenceAssets []assetReference `json:"reference_assets"`
}

type updateEpisodeRequest struct {
	Title          *string `json:"title"`
	Logline        *string `json:"logline"`
	TargetDuration *int    `json:"target_duration"`
	Status         *string `json:"status"`
	ExportStatus   *string `json:"export_status"`
}

type updateCharacterRequest struct {
	Name            *string          `json:"name"`
	AgeTag          *string          `json:"age_tag"`
	AppearanceDesc  *string          `json:"appearance_desc"`
	PersonalityDesc *string          `json:"personality_desc"`
	SpeakingStyle   *string          `json:"speaking_style"`
	CostumeDesc     *string          `json:"costume_desc"`
	LockedAttributes []string        `json:"locked_attributes"`
	ReferenceAssets []assetReference `json:"reference_assets"`
}

type updateLocationRequest struct {
	Name            *string          `json:"name"`
	Description     *string          `json:"description"`
	StyleTags       []string         `json:"style_tags"`
	ReferenceAssets []assetReference `json:"reference_assets"`
}

type updateSceneRequest struct {
	Summary              *string  `json:"summary"`
	InvolvedCharacterIDs []string `json:"involved_character_ids"`
	InvolvedLocationIDs  []string `json:"involved_location_ids"`
}

type updateShotRequest struct {
	OrderNo         *int    `json:"order_no"`
	Duration        *int    `json:"duration"`
	Description     *string `json:"description"`
	ShotType        *string `json:"shot_type"`
	CameraMotion    *string `json:"camera_motion"`
	SubjectDesc     *string `json:"subject_desc"`
	ActionDesc      *string `json:"action_desc"`
	EmotionDesc     *string `json:"emotion_desc"`
	DialogueText    *string `json:"dialogue_text"`
	GenerationMode  *string `json:"generation_mode"`
	Status          *string `json:"status"`
}

type storyCardGenerateRequest struct {
	CharacterIDs []string `json:"character_ids"`
	LocationIDs  []string `json:"location_ids"`
}

type storyboardGenerateRequest struct {
	CharacterIDs   []string `json:"character_ids"`
	LocationIDs    []string `json:"location_ids"`
	ReplaceExisting bool    `json:"replace_existing"`
}

type shotGenerateRequest struct {
	CandidateCount   int    `json:"candidate_count"`
	HighQuality      bool   `json:"high_quality"`
	InputType        string `json:"input_type"`
	PreferredProvider string `json:"preferred_provider"`
}

type renderEpisodeRequest struct {
	SelectedShotVersionIDs []string `json:"selected_shot_version_ids" binding:"required"`
	SubtitleText           string   `json:"subtitle_text"`
	VoiceAssetID           string   `json:"voice_asset_id"`
	BGMAssetID             string   `json:"bgm_asset_id"`
}

func NewApp(cfg config.Config, db *platformdb.DB, queueClient *queue.Queue, storageClient *storage.ObjectStorage) *App {
	return &App{
		cfg:     cfg,
		db:      db,
		queue:   queueClient,
		storage: storageClient,
		client: &stdhttp.Client{
			Timeout: 45 * time.Second,
		},
	}
}

func (a *App) Router() *gin.Engine {
	router := gin.Default()
	router.MaxMultipartMemory = 32 << 20
	router.GET("/healthz", a.handleHealth)
	router.GET("/api/openapi", a.handleOpenAPI)

	v1 := router.Group("/api/v1")
	{
		v1.GET("/projects", a.listProjects)
		v1.POST("/projects", a.createProject)
		v1.GET("/projects/:id", a.getProject)
		v1.POST("/projects/:id/episodes", a.createEpisode)
		v1.POST("/projects/:id/characters", a.createCharacter)
		v1.POST("/projects/:id/locations", a.createLocation)
		v1.POST("/projects/:id/assets:upload", a.uploadAsset)
		v1.GET("/episodes/:id", a.getEpisode)
		v1.PATCH("/episodes/:id", a.updateEpisode)
		v1.PATCH("/characters/:id", a.updateCharacter)
		v1.PATCH("/locations/:id", a.updateLocation)
		v1.PATCH("/scenes/:id", a.updateScene)
		v1.PATCH("/shots/:id", a.updateShot)
		v1.POST("/episodes/:id/story-card:generate", a.generateStoryCard)
		v1.POST("/episodes/:id/storyboard:generate", a.generateStoryboard)
		v1.POST("/shots/:id/generate", a.generateShot)
		v1.POST("/shots/:id/retry", a.generateShot)
		v1.POST("/shots/:id/versions/:versionId/select", a.selectShotVersion)
		v1.GET("/tasks/:id", a.getTask)
		v1.POST("/episodes/:id/render", a.createRenderJob)
		v1.GET("/render-jobs/:id", a.getRenderJob)
	}
	return router
}

func (a *App) handleHealth(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
	defer cancel()
	if err := a.db.Pool.Ping(ctx); err != nil {
		c.JSON(stdhttp.StatusServiceUnavailable, gin.H{"status": "degraded", "database": err.Error()})
		return
	}
	c.JSON(stdhttp.StatusOK, gin.H{"status": "ok"})
}

func (a *App) handleOpenAPI(c *gin.Context) {
	c.File("api/openapi.yaml")
}

func (a *App) listProjects(c *gin.Context) {
	rows, err := a.db.Pool.Query(c.Request.Context(), `
SELECT id, name, genre, style, aspect_ratio, target_duration, status, created_by, created_at, updated_at
FROM projects ORDER BY created_at DESC`)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	defer rows.Close()

	items := make([]projectRecord, 0)
	for rows.Next() {
		var item projectRecord
		if err := rows.Scan(&item.ID, &item.Name, &item.Genre, &item.Style, &item.AspectRatio, &item.TargetDuration, &item.Status, &item.CreatedBy, &item.CreatedAt, &item.UpdatedAt); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		items = append(items, item)
	}
	c.JSON(stdhttp.StatusOK, gin.H{"items": items})
}

func (a *App) createProject(c *gin.Context) {
	var req createProjectRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	if strings.TrimSpace(req.AspectRatio) == "" {
		req.AspectRatio = a.cfg.DefaultAspectRatio
	}

	projectID := uuid.New()
	now := time.Now().UTC()
	_, err := a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO projects(id, name, genre, style, aspect_ratio, target_duration, status, created_by, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
		projectID, req.Name, req.Genre, req.Style, req.AspectRatio, req.TargetDuration, "draft", req.CreatedBy, now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	project, err := a.loadProject(c.Request.Context(), projectID.String(), true)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusCreated, project)
}

func (a *App) getProject(c *gin.Context) {
	project, err := a.loadProject(c.Request.Context(), c.Param("id"), true)
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, project)
}

func (a *App) createEpisode(c *gin.Context) {
	var req createEpisodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	projectID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id := uuid.New()
	now := time.Now().UTC()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO episodes(id, project_id, title, logline, target_duration, status, export_status, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
		id, projectID, req.Title, req.Logline, req.TargetDuration, "draft", "draft", now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	episode, err := a.loadEpisode(c.Request.Context(), id.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusCreated, episode)
}

func (a *App) createCharacter(c *gin.Context) {
	var req createCharacterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	projectID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	payloadLocked, _ := json.Marshal(req.LockedAttributes)
	payloadRefs, _ := json.Marshal(req.ReferenceAssets)
	now := time.Now().UTC()
	id := uuid.New()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO characters(id, project_id, name, age_tag, appearance_desc, personality_desc, speaking_style, costume_desc, locked_attributes, reference_assets, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`,
		id, projectID, req.Name, req.AgeTag, req.AppearanceDesc, req.PersonalityDesc, req.SpeakingStyle, req.CostumeDesc, payloadLocked, payloadRefs, now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	character, err := a.loadCharacter(c.Request.Context(), id.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusCreated, character)
}

func (a *App) createLocation(c *gin.Context) {
	var req createLocationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	projectID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	payloadTags, _ := json.Marshal(req.StyleTags)
	payloadRefs, _ := json.Marshal(req.ReferenceAssets)
	now := time.Now().UTC()
	id := uuid.New()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO locations(id, project_id, name, description, reference_assets, style_tags, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8)`,
		id, projectID, req.Name, req.Description, payloadRefs, payloadTags, now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	location, err := a.loadLocation(c.Request.Context(), id.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusCreated, location)
}

func (a *App) uploadAsset(c *gin.Context) {
	projectID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	kind := strings.TrimSpace(c.PostForm("kind"))
	if kind == "" {
		kind = "reference_image"
	}
	fileHeader, err := c.FormFile("file")
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	file, err := fileHeader.Open()
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	defer file.Close()
	objectKey := storage.TimestampedObjectKey(filepath.Join("projects", projectID.String(), kind), fileHeader.Filename)
	uploaded, err := a.storage.UploadReader(c.Request.Context(), objectKey, file, fileHeader.Size, fileHeader.Header.Get("Content-Type"))
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	metadata, _ := json.Marshal(map[string]any{
		"filename":     fileHeader.Filename,
		"content_type": fileHeader.Header.Get("Content-Type"),
		"size":         fileHeader.Size,
	})
	id := uuid.New()
	now := time.Now().UTC()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO assets(id, project_id, kind, bucket, object_key, url, metadata, created_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8)`,
		id, projectID, kind, uploaded.Bucket, uploaded.ObjectKey, uploaded.URL, metadata, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	asset, err := a.loadAsset(c.Request.Context(), id.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusCreated, asset)
}

func (a *App) getEpisode(c *gin.Context) {
	episode, err := a.loadEpisode(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, episode)
}

func (a *App) updateEpisode(c *gin.Context) {
	var req updateEpisodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	_, err = a.db.Pool.Exec(c.Request.Context(), `
UPDATE episodes
SET title = COALESCE($2, title),
    logline = COALESCE($3, logline),
    target_duration = COALESCE($4, target_duration),
    status = COALESCE($5, status),
    export_status = COALESCE($6, export_status),
    updated_at = $7
WHERE id = $1`,
		id, req.Title, req.Logline, req.TargetDuration, req.Status, req.ExportStatus, time.Now().UTC(),
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	episode, err := a.loadEpisode(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, episode)
}

func (a *App) updateCharacter(c *gin.Context) {
	var req updateCharacterRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	current, err := a.loadCharacter(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	locked := current.LockedAttributes
	refs := current.ReferenceAssets
	if req.LockedAttributes != nil {
		locked = req.LockedAttributes
	}
	if req.ReferenceAssets != nil {
		refs = req.ReferenceAssets
	}
	payloadLocked, _ := json.Marshal(locked)
	payloadRefs, _ := json.Marshal(refs)
	_, err = a.db.Pool.Exec(c.Request.Context(), `
UPDATE characters
SET name = COALESCE($2, name),
    age_tag = COALESCE($3, age_tag),
    appearance_desc = COALESCE($4, appearance_desc),
    personality_desc = COALESCE($5, personality_desc),
    speaking_style = COALESCE($6, speaking_style),
    costume_desc = COALESCE($7, costume_desc),
    locked_attributes = $8,
    reference_assets = $9,
    updated_at = $10
WHERE id = $1`,
		id, req.Name, req.AgeTag, req.AppearanceDesc, req.PersonalityDesc, req.SpeakingStyle, req.CostumeDesc, payloadLocked, payloadRefs, time.Now().UTC(),
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	character, err := a.loadCharacter(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, character)
}

func (a *App) updateLocation(c *gin.Context) {
	var req updateLocationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	current, err := a.loadLocation(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	tags := current.StyleTags
	refs := current.ReferenceAssets
	if req.StyleTags != nil {
		tags = req.StyleTags
	}
	if req.ReferenceAssets != nil {
		refs = req.ReferenceAssets
	}
	payloadTags, _ := json.Marshal(tags)
	payloadRefs, _ := json.Marshal(refs)
	_, err = a.db.Pool.Exec(c.Request.Context(), `
UPDATE locations
SET name = COALESCE($2, name),
    description = COALESCE($3, description),
    style_tags = $4,
    reference_assets = $5,
    updated_at = $6
WHERE id = $1`,
		id, req.Name, req.Description, payloadTags, payloadRefs, time.Now().UTC(),
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	location, err := a.loadLocation(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, location)
}

func (a *App) updateScene(c *gin.Context) {
	var req updateSceneRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	scene, err := a.loadScene(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	if req.Summary != nil {
		scene.Summary = *req.Summary
	}
	if req.InvolvedCharacterIDs != nil {
		scene.InvolvedCharacterIDs = req.InvolvedCharacterIDs
	}
	if req.InvolvedLocationIDs != nil {
		scene.InvolvedLocationIDs = req.InvolvedLocationIDs
	}
	charactersJSON, _ := json.Marshal(scene.InvolvedCharacterIDs)
	locationsJSON, _ := json.Marshal(scene.InvolvedLocationIDs)
	_, err = a.db.Pool.Exec(c.Request.Context(), `
UPDATE scenes
SET summary = $2,
    involved_character_ids = $3,
    involved_location_ids = $4,
    updated_at = $5
WHERE id = $1`,
		id, scene.Summary, charactersJSON, locationsJSON, time.Now().UTC(),
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	updated, err := a.loadScene(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, updated)
}

func (a *App) updateShot(c *gin.Context) {
	var req updateShotRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	id, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	shot, err := a.loadShot(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	mergeShot(shot, req)
	if err := validateShot(shot); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	_, err = a.db.Pool.Exec(c.Request.Context(), `
UPDATE shots
SET order_no = $2,
    duration = $3,
    description = $4,
    shot_type = $5,
    camera_motion = $6,
    subject_desc = $7,
    action_desc = $8,
    emotion_desc = $9,
    dialogue_text = $10,
    generation_mode = $11,
    status = $12,
    updated_at = $13
WHERE id = $1`,
		id, shot.OrderNo, shot.Duration, shot.Description, shot.ShotType, shot.CameraMotion, shot.SubjectDesc, shot.ActionDesc, shot.EmotionDesc, shot.DialogueText, shot.GenerationMode, shot.Status, time.Now().UTC(),
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	updated, err := a.loadShot(c.Request.Context(), id.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, updated)
}

func (a *App) generateStoryCard(c *gin.Context) {
	var req storyCardGenerateRequest
	if err := c.ShouldBindJSON(&req); err != nil && !errors.Is(err, stdhttp.ErrNotMultipart) {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	episode, err := a.loadEpisode(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	project, err := a.loadProject(c.Request.Context(), episode.ProjectID.String(), false)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	characters, err := a.loadProjectCharacters(c.Request.Context(), episode.ProjectID)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	locations, err := a.loadProjectLocations(c.Request.Context(), episode.ProjectID)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	body := map[string]any{
		"project":      project,
		"episode":      episode,
		"characters":   filterByIDs(anySliceCharacters(characters), req.CharacterIDs),
		"locations":    filterByIDs(anySliceLocations(locations), req.LocationIDs),
	}
	response, err := a.postAI(c.Request.Context(), "/v1/story-card:generate", body)
	if err != nil {
		abort(c, stdhttp.StatusBadGateway, err)
		return
	}
	rawPayload, _ := json.Marshal(response)
	now := time.Now().UTC()
	storyID := uuid.New()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO story_cards(id, episode_id, theme, conflict, twist, ending_hook, summary, raw_payload, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
ON CONFLICT (episode_id) DO UPDATE SET
    theme = EXCLUDED.theme,
    conflict = EXCLUDED.conflict,
    twist = EXCLUDED.twist,
    ending_hook = EXCLUDED.ending_hook,
    summary = EXCLUDED.summary,
    raw_payload = EXCLUDED.raw_payload,
    updated_at = EXCLUDED.updated_at`,
		storyID, episode.ID, stringValue(response, "theme"), stringValue(response, "conflict"), stringValue(response, "twist"), stringValue(response, "ending_hook"), stringValue(response, "summary"), rawPayload, now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	_, err = a.db.Pool.Exec(c.Request.Context(), `UPDATE episodes SET status = $2, updated_at = $3 WHERE id = $1`, episode.ID, "story_ready", now)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	updated, err := a.loadEpisode(c.Request.Context(), episode.ID.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusOK, updated)
}

func (a *App) generateStoryboard(c *gin.Context) {
	var req storyboardGenerateRequest
	if err := c.ShouldBindJSON(&req); err != nil && !errors.Is(err, stdhttp.ErrNotMultipart) {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	episode, err := a.loadEpisode(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	if episode.StoryCard == nil {
		abort(c, stdhttp.StatusBadRequest, errors.New("story card must exist before storyboard generation"))
		return
	}
	project, err := a.loadProject(c.Request.Context(), episode.ProjectID.String(), false)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	characters, err := a.loadProjectCharacters(c.Request.Context(), episode.ProjectID)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	locations, err := a.loadProjectLocations(c.Request.Context(), episode.ProjectID)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	body := map[string]any{
		"project":      project,
		"episode":      episode,
		"story_card":   episode.StoryCard,
		"characters":   filterByIDs(anySliceCharacters(characters), req.CharacterIDs),
		"locations":    filterByIDs(anySliceLocations(locations), req.LocationIDs),
	}
	response, err := a.postAI(c.Request.Context(), "/v1/storyboard:generate", body)
	if err != nil {
		abort(c, stdhttp.StatusBadGateway, err)
		return
	}
	scenes, _ := response["scenes"].([]any)
	shots, _ := response["shots"].([]any)
	now := time.Now().UTC()
	tx, err := a.db.Pool.Begin(c.Request.Context())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	defer tx.Rollback(c.Request.Context())
	if req.ReplaceExisting {
		if _, err := tx.Exec(c.Request.Context(), "DELETE FROM shots WHERE episode_id = $1", episode.ID); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		if _, err := tx.Exec(c.Request.Context(), "DELETE FROM scenes WHERE episode_id = $1", episode.ID); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
	}
	sceneIDs := make(map[int]uuid.UUID)
	for index, raw := range scenes {
		item, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		sceneID := uuid.New()
		sceneIDs[index+1] = sceneID
		charactersJSON, _ := json.Marshal(stringSlice(item["involved_character_ids"]))
		locationsJSON, _ := json.Marshal(stringSlice(item["involved_location_ids"]))
		if _, err := tx.Exec(c.Request.Context(), `
INSERT INTO scenes(id, episode_id, order_no, summary, involved_character_ids, involved_location_ids, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8)`,
			sceneID, episode.ID, index+1, stringValue(item, "summary"), charactersJSON, locationsJSON, now, now,
		); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
	}
	for index, raw := range shots {
		item, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		shot := shotRecord{
			ID:             uuid.New(),
			EpisodeID:      episode.ID,
			OrderNo:        index + 1,
			Duration:       intValue(item["duration"], 4),
			Description:    stringValue(item, "description"),
			ShotType:       stringValue(item, "shot_type"),
			CameraMotion:   stringValue(item, "camera_motion"),
			SubjectDesc:    stringValue(item, "subject_desc"),
			ActionDesc:     stringValue(item, "action_desc"),
			EmotionDesc:    stringValue(item, "emotion_desc"),
			DialogueText:   stringValue(item, "dialogue_text"),
			GenerationMode: valueOr(item, "generation_mode", "text"),
			Status:         "draft",
			CreatedAt:      now,
			UpdatedAt:      now,
		}
		if err := validateShot(&shot); err != nil {
			abort(c, stdhttp.StatusBadRequest, err)
			return
		}
		if sceneIndex := intValue(item["scene_order"], 0); sceneIndex > 0 {
			if sceneID, ok := sceneIDs[sceneIndex]; ok {
				shot.SceneID = &sceneID
			}
		}
		if _, err := tx.Exec(c.Request.Context(), `
INSERT INTO shots(id, episode_id, scene_id, order_no, duration, description, shot_type, camera_motion, subject_desc, action_desc, emotion_desc, dialogue_text, generation_mode, status, current_version_id, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)`,
			shot.ID, shot.EpisodeID, shot.SceneID, shot.OrderNo, shot.Duration, shot.Description, shot.ShotType, shot.CameraMotion, shot.SubjectDesc, shot.ActionDesc, shot.EmotionDesc, shot.DialogueText, shot.GenerationMode, shot.Status, nil, shot.CreatedAt, shot.UpdatedAt,
		); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
	}
	if _, err := tx.Exec(c.Request.Context(), `UPDATE episodes SET status = $2, updated_at = $3 WHERE id = $1`, episode.ID, "storyboard_ready", now); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	if err := tx.Commit(c.Request.Context()); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	updated, err := a.loadEpisode(c.Request.Context(), episode.ID.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusOK, updated)
}

func (a *App) generateShot(c *gin.Context) {
	var req shotGenerateRequest
	if err := c.ShouldBindJSON(&req); err != nil && !errors.Is(err, stdhttp.ErrNotMultipart) {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	if req.CandidateCount == 0 {
		req.CandidateCount = 1
	}
	if req.CandidateCount < 1 || req.CandidateCount > 4 {
		abort(c, stdhttp.StatusBadRequest, errors.New("candidate_count must be between 1 and 4"))
		return
	}
	shot, err := a.loadShot(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	now := time.Now().UTC()
	taskIDs := make([]string, 0, req.CandidateCount)
	for index := 0; index < req.CandidateCount; index++ {
		taskID := uuid.New()
		payload, _ := json.Marshal(map[string]any{
			"shot_id":             shot.ID.String(),
			"candidate_count":     req.CandidateCount,
			"candidate_index":     index + 1,
			"high_quality":        req.HighQuality,
			"input_type":          valueOrMap(req.InputType, "text"),
			"preferred_provider":  req.PreferredProvider,
		})
		_, err := a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO generation_tasks(id, shot_id, provider, model, input_type, candidate_index, prompt_payload, status, raw_payload, output_asset_id, error_message, created_at, started_at, completed_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)`,
			taskID, shot.ID, "", "", valueOrMap(req.InputType, "text"), index+1, payload, "pending", []byte(`{}`), nil, nil, now, nil, nil, now,
		)
		if err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		if err := a.queue.Publish(c.Request.Context(), a.cfg.GenerationStream, queue.JobMessage{
			ID:   taskID.String(),
			Kind: "generate_shot",
			Payload: map[string]any{
				"task_id": taskID.String(),
				"shot_id": shot.ID.String(),
			},
		}); err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		taskIDs = append(taskIDs, taskID.String())
	}
	_, err = a.db.Pool.Exec(c.Request.Context(), `UPDATE shots SET status = $2, updated_at = $3 WHERE id = $1`, shot.ID, "generating", now)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusAccepted, gin.H{
		"shot_id":   shot.ID,
		"task_ids":  taskIDs,
		"status":    "generating",
	})
}

func (a *App) selectShotVersion(c *gin.Context) {
	versionID, err := uuid.Parse(c.Param("versionId"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	shotID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	tx, err := a.db.Pool.Begin(c.Request.Context())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	defer tx.Rollback(c.Request.Context())
	if _, err := tx.Exec(c.Request.Context(), `UPDATE shot_versions SET is_selected = false WHERE shot_id = $1`, shotID); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	if _, err := tx.Exec(c.Request.Context(), `UPDATE shot_versions SET is_selected = true WHERE id = $1`, versionID); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	if _, err := tx.Exec(c.Request.Context(), `UPDATE shots SET current_version_id = $2, status = $3, updated_at = $4 WHERE id = $1`, shotID, versionID, "success", time.Now().UTC()); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	if err := tx.Commit(c.Request.Context()); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	shot, err := a.loadShot(c.Request.Context(), shotID.String())
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, shot)
}

func (a *App) getTask(c *gin.Context) {
	task, err := a.loadTask(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, task)
}

func (a *App) createRenderJob(c *gin.Context) {
	var req renderEpisodeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	episodeID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		abort(c, stdhttp.StatusBadRequest, err)
		return
	}
	var subtitleAssetID *uuid.UUID
	if strings.TrimSpace(req.SubtitleText) != "" {
		episode, err := a.loadEpisode(c.Request.Context(), episodeID.String())
		if err != nil {
			handleLookupError(c, err)
			return
		}
		srt, metadata := renderSubtitleAsset(req.SubtitleText)
		objectKey := storage.TimestampedObjectKey(filepath.Join("projects", episode.ProjectID.String(), "subtitles"), episodeID.String()+".srt")
		uploaded, err := a.storage.UploadBytes(c.Request.Context(), objectKey, []byte(srt), "application/x-subrip")
		if err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		metaJSON, _ := json.Marshal(metadata)
		assetID := uuid.New()
		now := time.Now().UTC()
		_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO assets(id, project_id, kind, bucket, object_key, url, metadata, created_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8)`,
			assetID, episode.ProjectID, "subtitle", uploaded.Bucket, uploaded.ObjectKey, uploaded.URL, metaJSON, now,
		)
		if err != nil {
			abort(c, stdhttp.StatusInternalServerError, err)
			return
		}
		subtitleAssetID = &assetID
	}

	var voiceAssetID *uuid.UUID
	if strings.TrimSpace(req.VoiceAssetID) != "" {
		if parsed, err := uuid.Parse(req.VoiceAssetID); err == nil {
			voiceAssetID = &parsed
		}
	}
	var bgmAssetID *uuid.UUID
	if strings.TrimSpace(req.BGMAssetID) != "" {
		if parsed, err := uuid.Parse(req.BGMAssetID); err == nil {
			bgmAssetID = &parsed
		}
	}

	jobID := uuid.New()
	payloadVersions, _ := json.Marshal(req.SelectedShotVersionIDs)
	now := time.Now().UTC()
	_, err = a.db.Pool.Exec(c.Request.Context(), `
INSERT INTO render_jobs(id, episode_id, selected_shot_version_ids, subtitle_asset_id, voice_asset_id, bgm_asset_id, output_asset_id, status, metadata, error_message, created_at, updated_at)
VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`,
		jobID, episodeID, payloadVersions, subtitleAssetID, voiceAssetID, bgmAssetID, nil, "pending", []byte(`{}`), nil, now, now,
	)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	_, err = a.db.Pool.Exec(c.Request.Context(), `UPDATE episodes SET export_status = $2, updated_at = $3 WHERE id = $1`, episodeID, "pending", now)
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	if err := a.queue.Publish(c.Request.Context(), a.cfg.RenderStream, queue.JobMessage{
		ID:   jobID.String(),
		Kind: "render_episode",
		Payload: map[string]any{
			"render_job_id": jobID.String(),
			"episode_id":    episodeID.String(),
		},
	}); err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	job, err := a.loadRenderJob(c.Request.Context(), jobID.String())
	if err != nil {
		abort(c, stdhttp.StatusInternalServerError, err)
		return
	}
	c.JSON(stdhttp.StatusAccepted, job)
}

func (a *App) getRenderJob(c *gin.Context) {
	job, err := a.loadRenderJob(c.Request.Context(), c.Param("id"))
	if err != nil {
		handleLookupError(c, err)
		return
	}
	c.JSON(stdhttp.StatusOK, job)
}

func (a *App) StartRenderWorker(ctx context.Context) {
	consumer := "backend-render"
	for {
		if ctx.Err() != nil {
			return
		}
		messages, err := a.queue.Consume(ctx, a.cfg.RenderStream, queue.RenderConsumerGroup, consumer, a.cfg.RenderPollInterval, 1)
		if err != nil || len(messages) == 0 {
			time.Sleep(2 * time.Second)
			continue
		}
		ackIDs := make([]string, 0, len(messages))
		for _, message := range messages {
			rawMessage, _ := message.Values["message"].(string)
			var job queue.JobMessage
			if err := json.Unmarshal([]byte(rawMessage), &job); err != nil {
				ackIDs = append(ackIDs, message.ID)
				continue
			}
			if err := a.runRenderJob(ctx, job.ID); err == nil {
				ackIDs = append(ackIDs, message.ID)
			}
		}
		_ = a.queue.Ack(ctx, a.cfg.RenderStream, queue.RenderConsumerGroup, ackIDs...)
	}
}

func (a *App) runRenderJob(ctx context.Context, renderJobID string) error {
	job, err := a.loadRenderJob(ctx, renderJobID)
	if err != nil {
		return err
	}
	now := time.Now().UTC()
	if _, err := a.db.Pool.Exec(ctx, `UPDATE render_jobs SET status = $2, updated_at = $3 WHERE id = $1`, job.ID, "processing", now); err != nil {
		return err
	}
	if _, err := a.db.Pool.Exec(ctx, `UPDATE episodes SET export_status = $2, updated_at = $3 WHERE id = $1`, job.EpisodeID, "processing", now); err != nil {
		return err
	}

	versionIDs := make([]uuid.UUID, 0, len(job.SelectedShotVersionIDs))
	for _, raw := range job.SelectedShotVersionIDs {
		parsed, err := uuid.Parse(raw)
		if err == nil {
			versionIDs = append(versionIDs, parsed)
		}
	}
	versions, err := a.loadShotVersionsByIDs(ctx, versionIDs)
	if err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	if len(versions) == 0 {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, errors.New("no shot versions selected"))
	}
	tmpDir := filepath.Join("tmp", "renders", job.ID.String())
	concatFile := filepath.Join(tmpDir, "concat.txt")
	outputFile := filepath.Join(tmpDir, "output.mp4")
	if err := ensureDir(tmpDir); err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	paths := make([]string, 0, len(versions))
	for index, version := range versions {
		if version.AssetURL == "" {
			continue
		}
		targetPath := filepath.Join(tmpDir, fmt.Sprintf("%02d-%s.mp4", index+1, version.ID.String()))
		if err := downloadToFile(version.AssetURL, targetPath); err != nil {
			return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
		}
		paths = append(paths, targetPath)
	}
	if len(paths) == 0 {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, errors.New("selected shot versions do not have downloadable assets"))
	}
	if err := buildConcatFile(concatFile, paths); err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	args := []string{"-y", "-f", "concat", "-safe", "0", "-i", concatFile}
	if job.SubtitleAssetID != nil {
		subtitleAsset, err := a.loadAsset(ctx, job.SubtitleAssetID.String())
		if err == nil {
			subtitleFile := filepath.Join(tmpDir, "subtitles.srt")
			if err := downloadToFile(subtitleAsset.URL, subtitleFile); err == nil {
				args = append(args, "-vf", "subtitles="+subtitleFile)
			}
		}
	}
	args = append(args, "-c", "copy", outputFile)
	if output, err := exec.CommandContext(ctx, "ffmpeg", args...).CombinedOutput(); err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, fmt.Errorf("ffmpeg render: %w (%s)", err, string(output)))
	}
	content, err := os.ReadFile(outputFile)
	if err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	objectKey := storage.TimestampedObjectKey(filepath.Join("episodes", job.EpisodeID.String(), "exports"), "render.mp4")
	uploaded, err := a.storage.UploadBytes(ctx, objectKey, content, "video/mp4")
	if err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	metaJSON, _ := json.Marshal(map[string]any{
		"render_job_id": job.ID.String(),
		"shot_version_ids": job.SelectedShotVersionIDs,
	})
	assetID := uuid.New()
	if _, err := a.db.Pool.Exec(ctx, `
INSERT INTO assets(id, project_id, kind, bucket, object_key, url, metadata, created_at)
SELECT $1, episodes.project_id, $2, $3, $4, $5, $6, $7 FROM episodes WHERE episodes.id = $8`,
		assetID, "render_output", uploaded.Bucket, uploaded.ObjectKey, uploaded.URL, metaJSON, time.Now().UTC(), job.EpisodeID,
	); err != nil {
		return a.failRenderJob(ctx, job.ID, job.EpisodeID, err)
	}
	if _, err := a.db.Pool.Exec(ctx, `
UPDATE render_jobs SET status = $2, output_asset_id = $3, updated_at = $4 WHERE id = $1`,
		job.ID, "success", assetID, time.Now().UTC(),
	); err != nil {
		return err
	}
	if _, err := a.db.Pool.Exec(ctx, `
UPDATE episodes SET export_status = $2, status = $3, updated_at = $4 WHERE id = $1`,
		job.EpisodeID, "success", "assembled", time.Now().UTC(),
	); err != nil {
		return err
	}
	return nil
}

func (a *App) failRenderJob(ctx context.Context, jobID, episodeID uuid.UUID, err error) error {
	msg := err.Error()
	if _, execErr := a.db.Pool.Exec(ctx, `UPDATE render_jobs SET status = $2, error_message = $3, updated_at = $4 WHERE id = $1`, jobID, "failed", msg, time.Now().UTC()); execErr != nil {
		return execErr
	}
	_, _ = a.db.Pool.Exec(ctx, `UPDATE episodes SET export_status = $2, updated_at = $3 WHERE id = $1`, episodeID, "failed", time.Now().UTC())
	return err
}

func (a *App) postAI(ctx context.Context, endpoint string, body map[string]any) (map[string]any, error) {
	payload, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	req, err := stdhttp.NewRequestWithContext(ctx, stdhttp.MethodPost, strings.TrimRight(a.cfg.AIServiceBaseURL, "/")+endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := a.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		var errorBody bytes.Buffer
		_, _ = errorBody.ReadFrom(resp.Body)
		return nil, fmt.Errorf("ai service returned %d: %s", resp.StatusCode, errorBody.String())
	}
	var output map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&output); err != nil {
		return nil, err
	}
	return output, nil
}

func (a *App) loadProject(ctx context.Context, rawID string, withNested bool) (*projectRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	var item projectRecord
	if err := a.db.Pool.QueryRow(ctx, `
SELECT id, name, genre, style, aspect_ratio, target_duration, status, created_by, created_at, updated_at
FROM projects WHERE id = $1`, id,
	).Scan(&item.ID, &item.Name, &item.Genre, &item.Style, &item.AspectRatio, &item.TargetDuration, &item.Status, &item.CreatedBy, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return nil, err
	}
	if withNested {
		episodes, _ := a.loadProjectEpisodes(ctx, item.ID)
		characters, _ := a.loadProjectCharacters(ctx, item.ID)
		locations, _ := a.loadProjectLocations(ctx, item.ID)
		item.Episodes = anySliceEpisodes(episodes)
		item.Characters = anySliceCharacters(characters)
		item.Locations = anySliceLocations(locations)
	}
	return &item, nil
}

func (a *App) loadProjectEpisodes(ctx context.Context, projectID uuid.UUID) ([]episodeRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, project_id, title, logline, target_duration, status, export_status, created_at, updated_at
FROM episodes WHERE project_id = $1 ORDER BY created_at DESC`, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]episodeRecord, 0)
	for rows.Next() {
		var item episodeRecord
		if err := rows.Scan(&item.ID, &item.ProjectID, &item.Title, &item.Logline, &item.TargetDuration, &item.Status, &item.ExportStatus, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadProjectCharacters(ctx context.Context, projectID uuid.UUID) ([]characterRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, project_id, name, age_tag, appearance_desc, personality_desc, speaking_style, costume_desc, locked_attributes, reference_assets, created_at, updated_at
FROM characters WHERE project_id = $1 ORDER BY created_at ASC`, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]characterRecord, 0)
	for rows.Next() {
		item, err := scanCharacter(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadProjectLocations(ctx context.Context, projectID uuid.UUID) ([]locationRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, project_id, name, description, reference_assets, style_tags, created_at, updated_at
FROM locations WHERE project_id = $1 ORDER BY created_at ASC`, projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]locationRecord, 0)
	for rows.Next() {
		item, err := scanLocation(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadCharacter(ctx context.Context, rawID string) (*characterRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, project_id, name, age_tag, appearance_desc, personality_desc, speaking_style, costume_desc, locked_attributes, reference_assets, created_at, updated_at
FROM characters WHERE id = $1`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, pgx.ErrNoRows
	}
	item, err := scanCharacter(rows)
	if err != nil {
		return nil, err
	}
	return &item, nil
}

func (a *App) loadLocation(ctx context.Context, rawID string) (*locationRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, project_id, name, description, reference_assets, style_tags, created_at, updated_at
FROM locations WHERE id = $1`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, pgx.ErrNoRows
	}
	item, err := scanLocation(rows)
	if err != nil {
		return nil, err
	}
	return &item, nil
}

func (a *App) loadEpisode(ctx context.Context, rawID string) (*episodeRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	var item episodeRecord
	if err := a.db.Pool.QueryRow(ctx, `
SELECT id, project_id, title, logline, target_duration, status, export_status, created_at, updated_at
FROM episodes WHERE id = $1`, id,
	).Scan(&item.ID, &item.ProjectID, &item.Title, &item.Logline, &item.TargetDuration, &item.Status, &item.ExportStatus, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return nil, err
	}
	storyCard, _ := a.loadStoryCardByEpisode(ctx, item.ID)
	item.StoryCard = storyCard
	scenes, _ := a.loadScenesByEpisode(ctx, item.ID)
	shots, _ := a.loadShotsByEpisode(ctx, item.ID)
	renderJobs, _ := a.loadRenderJobsByEpisode(ctx, item.ID)
	item.Scenes = scenes
	item.Shots = shots
	item.RenderJobs = renderJobs
	return &item, nil
}

func (a *App) loadStoryCardByEpisode(ctx context.Context, episodeID uuid.UUID) (*storyCardRecord, error) {
	var item storyCardRecord
	err := a.db.Pool.QueryRow(ctx, `
SELECT id, episode_id, theme, conflict, twist, ending_hook, summary, raw_payload, created_at, updated_at
FROM story_cards WHERE episode_id = $1`, episodeID,
	).Scan(&item.ID, &item.EpisodeID, &item.Theme, &item.Conflict, &item.Twist, &item.EndingHook, &item.Summary, &item.RawPayload, &item.CreatedAt, &item.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &item, nil
}

func (a *App) loadScenesByEpisode(ctx context.Context, episodeID uuid.UUID) ([]sceneRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, episode_id, order_no, summary, involved_character_ids, involved_location_ids, created_at, updated_at
FROM scenes WHERE episode_id = $1 ORDER BY order_no ASC`, episodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]sceneRecord, 0)
	for rows.Next() {
		var item sceneRecord
		var characterJSON []byte
		var locationJSON []byte
		if err := rows.Scan(&item.ID, &item.EpisodeID, &item.OrderNo, &item.Summary, &characterJSON, &locationJSON, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, err
		}
		_ = json.Unmarshal(characterJSON, &item.InvolvedCharacterIDs)
		_ = json.Unmarshal(locationJSON, &item.InvolvedLocationIDs)
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadScene(ctx context.Context, rawID string) (*sceneRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, episode_id, order_no, summary, involved_character_ids, involved_location_ids, created_at, updated_at
FROM scenes WHERE id = $1`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, pgx.ErrNoRows
	}
	var item sceneRecord
	var characterJSON []byte
	var locationJSON []byte
	if err := rows.Scan(&item.ID, &item.EpisodeID, &item.OrderNo, &item.Summary, &characterJSON, &locationJSON, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return nil, err
	}
	_ = json.Unmarshal(characterJSON, &item.InvolvedCharacterIDs)
	_ = json.Unmarshal(locationJSON, &item.InvolvedLocationIDs)
	return &item, nil
}

func (a *App) loadShotsByEpisode(ctx context.Context, episodeID uuid.UUID) ([]shotRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT id, episode_id, scene_id, order_no, duration, description, shot_type, camera_motion, subject_desc, action_desc, emotion_desc, dialogue_text, generation_mode, status, current_version_id, created_at, updated_at
FROM shots WHERE episode_id = $1 ORDER BY order_no ASC`, episodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]shotRecord, 0)
	for rows.Next() {
		var item shotRecord
		if err := rows.Scan(&item.ID, &item.EpisodeID, &item.SceneID, &item.OrderNo, &item.Duration, &item.Description, &item.ShotType, &item.CameraMotion, &item.SubjectDesc, &item.ActionDesc, &item.EmotionDesc, &item.DialogueText, &item.GenerationMode, &item.Status, &item.CurrentVersionID, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, err
		}
		versions, _ := a.loadShotVersionsByShot(ctx, item.ID)
		item.Versions = anySliceVersions(versions)
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadShot(ctx context.Context, rawID string) (*shotRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	var item shotRecord
	if err := a.db.Pool.QueryRow(ctx, `
SELECT id, episode_id, scene_id, order_no, duration, description, shot_type, camera_motion, subject_desc, action_desc, emotion_desc, dialogue_text, generation_mode, status, current_version_id, created_at, updated_at
FROM shots WHERE id = $1`, id,
	).Scan(&item.ID, &item.EpisodeID, &item.SceneID, &item.OrderNo, &item.Duration, &item.Description, &item.ShotType, &item.CameraMotion, &item.SubjectDesc, &item.ActionDesc, &item.EmotionDesc, &item.DialogueText, &item.GenerationMode, &item.Status, &item.CurrentVersionID, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return nil, err
	}
	versions, _ := a.loadShotVersionsByShot(ctx, item.ID)
	item.Versions = anySliceVersions(versions)
	return &item, nil
}

func (a *App) loadShotVersionsByShot(ctx context.Context, shotID uuid.UUID) ([]shotVersionRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT sv.id, sv.shot_id, sv.task_id, sv.asset_id, sv.provider, sv.model, sv.is_selected, sv.prompt_payload, sv.metadata, sv.created_at, assets.url
FROM shot_versions sv
JOIN assets ON assets.id = sv.asset_id
WHERE sv.shot_id = $1
ORDER BY sv.created_at DESC`, shotID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]shotVersionRecord, 0)
	for rows.Next() {
		var item shotVersionRecord
		if err := rows.Scan(&item.ID, &item.ShotID, &item.TaskID, &item.AssetID, &item.Provider, &item.Model, &item.IsSelected, &item.PromptPayload, &item.Metadata, &item.CreatedAt, &item.AssetURL); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadShotVersionsByIDs(ctx context.Context, ids []uuid.UUID) ([]shotVersionRecord, error) {
	items := make([]shotVersionRecord, 0, len(ids))
	for _, id := range ids {
		var item shotVersionRecord
		if err := a.db.Pool.QueryRow(ctx, `
SELECT sv.id, sv.shot_id, sv.task_id, sv.asset_id, sv.provider, sv.model, sv.is_selected, sv.prompt_payload, sv.metadata, sv.created_at, assets.url
FROM shot_versions sv
JOIN assets ON assets.id = sv.asset_id
WHERE sv.id = $1`, id,
		).Scan(&item.ID, &item.ShotID, &item.TaskID, &item.AssetID, &item.Provider, &item.Model, &item.IsSelected, &item.PromptPayload, &item.Metadata, &item.CreatedAt, &item.AssetURL); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadAsset(ctx context.Context, rawID string) (*assetRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	var item assetRecord
	if err := a.db.Pool.QueryRow(ctx, `
SELECT id, project_id, kind, bucket, object_key, url, metadata, created_at
FROM assets WHERE id = $1`, id,
	).Scan(&item.ID, &item.ProjectID, &item.Kind, &item.Bucket, &item.ObjectKey, &item.URL, &item.Metadata, &item.CreatedAt); err != nil {
		return nil, err
	}
	return &item, nil
}

func (a *App) loadTask(ctx context.Context, rawID string) (*taskRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	var item taskRecord
	if err := a.db.Pool.QueryRow(ctx, `
SELECT id, shot_id, provider, model, input_type, candidate_index, prompt_payload, status, raw_payload, output_asset_id, error_message, created_at, started_at, completed_at, updated_at
FROM generation_tasks WHERE id = $1`, id,
	).Scan(&item.ID, &item.ShotID, &item.Provider, &item.Model, &item.InputType, &item.CandidateIndex, &item.PromptPayload, &item.Status, &item.RawPayload, &item.OutputAssetID, &item.ErrorMessage, &item.CreatedAt, &item.StartedAt, &item.CompletedAt, &item.UpdatedAt); err != nil {
		return nil, err
	}
	return &item, nil
}

func (a *App) loadRenderJobsByEpisode(ctx context.Context, episodeID uuid.UUID) ([]renderJobRecord, error) {
	rows, err := a.db.Pool.Query(ctx, `
SELECT r.id, r.episode_id, r.selected_shot_version_ids, r.subtitle_asset_id, r.voice_asset_id, r.bgm_asset_id, r.output_asset_id, r.status, r.metadata, r.error_message, r.created_at, r.updated_at, assets.url
FROM render_jobs r
LEFT JOIN assets ON assets.id = r.output_asset_id
WHERE r.episode_id = $1
ORDER BY r.created_at DESC`, episodeID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]renderJobRecord, 0)
	for rows.Next() {
		item, err := scanRenderJob(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, nil
}

func (a *App) loadRenderJob(ctx context.Context, rawID string) (*renderJobRecord, error) {
	id, err := uuid.Parse(rawID)
	if err != nil {
		return nil, err
	}
	rows, err := a.db.Pool.Query(ctx, `
SELECT r.id, r.episode_id, r.selected_shot_version_ids, r.subtitle_asset_id, r.voice_asset_id, r.bgm_asset_id, r.output_asset_id, r.status, r.metadata, r.error_message, r.created_at, r.updated_at, assets.url
FROM render_jobs r
LEFT JOIN assets ON assets.id = r.output_asset_id
WHERE r.id = $1`, id)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	if !rows.Next() {
		return nil, pgx.ErrNoRows
	}
	item, err := scanRenderJob(rows)
	if err != nil {
		return nil, err
	}
	return &item, nil
}

func scanCharacter(rows pgx.Rows) (characterRecord, error) {
	var item characterRecord
	var lockedJSON []byte
	var refsJSON []byte
	if err := rows.Scan(&item.ID, &item.ProjectID, &item.Name, &item.AgeTag, &item.AppearanceDesc, &item.PersonalityDesc, &item.SpeakingStyle, &item.CostumeDesc, &lockedJSON, &refsJSON, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return item, err
	}
	_ = json.Unmarshal(lockedJSON, &item.LockedAttributes)
	_ = json.Unmarshal(refsJSON, &item.ReferenceAssets)
	return item, nil
}

func scanLocation(rows pgx.Rows) (locationRecord, error) {
	var item locationRecord
	var refsJSON []byte
	var tagsJSON []byte
	if err := rows.Scan(&item.ID, &item.ProjectID, &item.Name, &item.Description, &refsJSON, &tagsJSON, &item.CreatedAt, &item.UpdatedAt); err != nil {
		return item, err
	}
	_ = json.Unmarshal(tagsJSON, &item.StyleTags)
	_ = json.Unmarshal(refsJSON, &item.ReferenceAssets)
	return item, nil
}

func scanRenderJob(rows pgx.Rows) (renderJobRecord, error) {
	var item renderJobRecord
	var selectedJSON []byte
	var outputURL *string
	if err := rows.Scan(&item.ID, &item.EpisodeID, &selectedJSON, &item.SubtitleAssetID, &item.VoiceAssetID, &item.BGMAssetID, &item.OutputAssetID, &item.Status, &item.Metadata, &item.ErrorMessage, &item.CreatedAt, &item.UpdatedAt, &outputURL); err != nil {
		return item, err
	}
	_ = json.Unmarshal(selectedJSON, &item.SelectedShotVersionIDs)
	item.OutputURL = outputURL
	return item, nil
}

func validateShot(item *shotRecord) error {
	if item.Duration < 3 || item.Duration > 8 {
		return errors.New("shot duration must be between 3 and 8 seconds")
	}
	return nil
}

func mergeShot(item *shotRecord, req updateShotRequest) {
	if req.OrderNo != nil {
		item.OrderNo = *req.OrderNo
	}
	if req.Duration != nil {
		item.Duration = *req.Duration
	}
	if req.Description != nil {
		item.Description = *req.Description
	}
	if req.ShotType != nil {
		item.ShotType = *req.ShotType
	}
	if req.CameraMotion != nil {
		item.CameraMotion = *req.CameraMotion
	}
	if req.SubjectDesc != nil {
		item.SubjectDesc = *req.SubjectDesc
	}
	if req.ActionDesc != nil {
		item.ActionDesc = *req.ActionDesc
	}
	if req.EmotionDesc != nil {
		item.EmotionDesc = *req.EmotionDesc
	}
	if req.DialogueText != nil {
		item.DialogueText = *req.DialogueText
	}
	if req.GenerationMode != nil {
		item.GenerationMode = *req.GenerationMode
	}
	if req.Status != nil {
		item.Status = *req.Status
	}
}

func renderSubtitleAsset(text string) (string, map[string]any) {
	lines := strings.Split(text, "\n")
	builder := strings.Builder{}
	cursor := 0
	for index, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		builder.WriteString(strconv.Itoa(index + 1))
		builder.WriteString("\n")
		start := formatSRTTimestamp(cursor)
		cursor += 3
		end := formatSRTTimestamp(cursor)
		builder.WriteString(start + " --> " + end + "\n")
		builder.WriteString(trimmed + "\n\n")
	}
	return builder.String(), map[string]any{
		"line_count": len(lines),
	}
}

func formatSRTTimestamp(seconds int) string {
	hours := seconds / 3600
	minutes := (seconds % 3600) / 60
	secs := seconds % 60
	return fmt.Sprintf("%02d:%02d:%02d,000", hours, minutes, secs)
}

func handleLookupError(c *gin.Context, err error) {
	if errors.Is(err, pgx.ErrNoRows) {
		abort(c, stdhttp.StatusNotFound, err)
		return
	}
	abort(c, stdhttp.StatusInternalServerError, err)
}

func abort(c *gin.Context, status int, err error) {
	c.AbortWithStatusJSON(status, gin.H{
		"error": err.Error(),
	})
}

func valueOrMap(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}

func valueOr(item map[string]any, key, fallback string) string {
	value := strings.TrimSpace(stringValue(item, key))
	if value == "" {
		return fallback
	}
	return value
}

func stringValue(item map[string]any, key string) string {
	value, ok := item[key]
	if !ok || value == nil {
		return ""
	}
	switch typed := value.(type) {
	case string:
		return typed
	default:
		return fmt.Sprintf("%v", typed)
	}
}

func intValue(value any, fallback int) int {
	switch typed := value.(type) {
	case int:
		return typed
	case int32:
		return int(typed)
	case int64:
		return int(typed)
	case float64:
		return int(typed)
	case string:
		if parsed, err := strconv.Atoi(typed); err == nil {
			return parsed
		}
	}
	return fallback
}

func stringSlice(value any) []string {
	switch typed := value.(type) {
	case []string:
		return typed
	case []any:
		output := make([]string, 0, len(typed))
		for _, item := range typed {
			output = append(output, fmt.Sprintf("%v", item))
		}
		return output
	default:
		return nil
	}
}

func anySliceEpisodes(items []episodeRecord) []any {
	out := make([]any, 0, len(items))
	for _, item := range items {
		out = append(out, item)
	}
	return out
}

func anySliceCharacters(items []characterRecord) []any {
	out := make([]any, 0, len(items))
	for _, item := range items {
		out = append(out, item)
	}
	return out
}

func anySliceLocations(items []locationRecord) []any {
	out := make([]any, 0, len(items))
	for _, item := range items {
		out = append(out, item)
	}
	return out
}

func anySliceVersions(items []shotVersionRecord) []any {
	out := make([]any, 0, len(items))
	for _, item := range items {
		out = append(out, item)
	}
	return out
}

func filterByIDs(items []any, ids []string) []any {
	if len(ids) == 0 {
		return items
	}
	lookup := make(map[string]struct{}, len(ids))
	for _, id := range ids {
		lookup[id] = struct{}{}
	}
	filtered := make([]any, 0)
	for _, item := range items {
		raw, _ := json.Marshal(item)
		var decoded map[string]any
		if err := json.Unmarshal(raw, &decoded); err != nil {
			continue
		}
		id := stringValue(decoded, "id")
		if _, ok := lookup[id]; ok {
			filtered = append(filtered, item)
		}
	}
	return filtered
}

func ensureDir(path string) error {
	return exec.Command("mkdir", "-p", path).Run()
}

func buildConcatFile(filename string, inputs []string) error {
	var builder strings.Builder
	for _, input := range inputs {
		builder.WriteString("file '" + input + "'\n")
	}
	return os.WriteFile(filename, []byte(builder.String()), 0o644)
}

func downloadToFile(sourceURL string, filename string) error {
	response, err := stdhttp.Get(sourceURL)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode >= 300 {
		return fmt.Errorf("download asset: status %d", response.StatusCode)
	}
	content, err := io.ReadAll(response.Body)
	if err != nil {
		return err
	}
	return os.WriteFile(filename, content, 0o644)
}
