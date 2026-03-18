package http

import (
	"strings"
	"testing"
)

func TestValidateShotDuration(t *testing.T) {
	shot := &shotRecord{Duration: 2}
	if err := validateShot(shot); err == nil {
		t.Fatalf("expected validation error for duration below minimum")
	}

	shot.Duration = 4
	if err := validateShot(shot); err != nil {
		t.Fatalf("expected duration 4 to be valid, got %v", err)
	}
}

func TestRenderSubtitleAssetBuildsSRT(t *testing.T) {
	srt, metadata := renderSubtitleAsset("第一句\n第二句")
	if !strings.Contains(srt, "00:00:00,000 --> 00:00:03,000") {
		t.Fatalf("expected first subtitle timestamp in output, got %s", srt)
	}
	if metadata["line_count"] != 2 {
		t.Fatalf("expected 2 lines in metadata, got %#v", metadata)
	}
}
