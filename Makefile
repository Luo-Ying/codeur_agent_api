.PHONY: build run rebuild-run stop logs

build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

build-run: build run

rebuild-run: stop build run

logs:
	docker compose logs -f