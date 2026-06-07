package handler

import (
	"auth-service/internal/usecase"
	dto "auth-service/internal/transport/http"
	"encoding/json"
	"net/http"
)




type AuthHandler struct{
	registerUseCase *usecase.RegisterUsecase
}

func NewAuthHandler(
	registerUsecase *usecase.RegisterUsecase,
) *AuthHandler{
	return &AuthHandler{
		registerUseCase: registerUsecase,
	}
}

func(h *AuthHandler) Register(
	w http.ResponseWriter,
	r *http.Request,
){

	var req dto.RegisterRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil{
		http.Error(w, "Invalid Request", http.StatusBadRequest)
		return
	}

	err := h.registerUseCase.Register(
		req.FirstName,
		req.LastName,
		req.Email,
		req.Password,
	)

	if err != nil{
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.WriteHeader(http.StatusCreated)

	json.NewEncoder(w).Encode(map[string]string{
		"message": "user registered successfully",
	})

}