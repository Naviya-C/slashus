package service

import (
	"fmt"

	"crypto/rand"
	"encoding/base64"

	"golang.org/x/crypto/argon2"
)


type PasswordService interface{
	Hash(password string) (string, error)
	Verify(password, hash string) error
}

type Argon2idPasswordService struct{}

func NewArgon2idPasswordService() *Argon2idPasswordService {
	return &Argon2idPasswordService{}
}

func(a *Argon2idPasswordService) Hash(
	password string,
) (string, error){
	//Generate Random Salt
	salt := make([]byte, 16)

	_, err := rand.Read(salt)

	if err != nil{
		return "", err
	}

	//Generate argon hash
	hash := argon2.IDKey(
		[]byte(password),
		salt,
		3,
		64*1024,
		2,
		32,
	)

	saltEncoder := base64.RawStdEncoding.EncodeToString((salt))
	hashEncoder := base64.RawStdEncoding.EncodeToString(hash)

	encodedHash := fmt.Sprintf(
		"$argon2id$v=19$m=65536,t=3,p=2$%s$%s",
		saltEncoder,
		hashEncoder,
	)

	return  encodedHash, nil
}