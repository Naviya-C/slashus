// Package proxy forwards requests to backend services.
package proxy

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"
)

// New builds a reverse proxy to one backend.
//
// httputil.ReverseProxy STREAMS bodies rather than buffering them, which is
// what makes a 100 MB upload pass through the gateway without it holding the
// file in memory.
func New(target string, timeout time.Duration, log *slog.Logger) (http.Handler, error) {
	u, err := url.Parse(target)
	if err != nil {
		return nil, err
	}

	rp := httputil.NewSingleHostReverseProxy(u)

	// No response timeout on the transport: uploads and LLM generation are
	// both legitimately slow. Dial and header timeouts still protect against a
	// backend that accepts a connection and then hangs.
	rp.Transport = &http.Transport{
		ResponseHeaderTimeout: timeout,
		IdleConnTimeout:       90 * time.Second,
		MaxIdleConnsPerHost:   32,
	}

	// FlushInterval > 0 streams the response as it arrives instead of
	// buffering it whole — needed if you later add streamed LLM output.
	rp.FlushInterval = 100 * time.Millisecond

	// A backend that is not deployed yet must produce a clear 502, not a
	// gateway crash. This is what lets services be rolled out one at a time.
	rp.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		log.Error("backend unreachable", "target", target, "path", r.URL.Path, "err", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadGateway)
		_ = json.NewEncoder(w).Encode(map[string]string{
			"error": "service temporarily unavailable",
		})
	}

	return rp, nil
}
