.PHONY: build run rebuild-run stop logs

build:
	docker build -t codeur-agent-api-image .

run:
	docker rm codeur-agent-api-container || true
	docker run -d --name codeur-agent-api-container -p 8000:8000 --env-file .env codeur-agent-api-image

stop:
	docker stop codeur-agent-api-container

rebuild-run: stop build run

logs:
	docker logs -f codeur-agent-api-container