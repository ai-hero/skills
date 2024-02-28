build:
	docker compose build

run: build
	docker compose up --remove-orphans

clean:
	docker compose down