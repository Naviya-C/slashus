package handler

import (
	"auth-service/internal/usecase"
	dto "auth-service/internal/transport"
	"encoding/json"
	"net/http"
)


type AuthHandler struct{
	registerUseCase *usecase.RegisterUsecase
	loginUseCase *usecase.LoginUseCase
}

func NewAuthHandler(
	registerUsecase *usecase.RegisterUsecase,
	loginUseCase *usecase.LoginUseCase,
) *AuthHandler{
	return &AuthHandler{
		registerUseCase: registerUsecase,
		loginUseCase: loginUseCase,
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

func (l *AuthHandler) Login(
	w http.ResponseWriter,
	r *http.Request,
){
	var req dto.LoginRequest

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil{
		http.Error(w, "Invalid Request", http.StatusBadRequest)
		return
	}

	token, err := l.loginUseCase.Login(req.Email, req.Password)

	if err != nil{
		http.Error(w, err.Error(), http.StatusUnauthorized)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	json.NewEncoder(w).Encode(map[string]string{
		"message": "Login Success",
		"token": token,
	})
}