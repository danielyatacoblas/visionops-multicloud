FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data/sample ./data/sample
RUN pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "visionops"]
CMD ["--input", "data/sample", "--output", "artifacts"]
