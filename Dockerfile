FROM python:3.12-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
RUN chown app:app /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
USER app
RUN python -c "import solcx; solcx.install_solc('0.8.24')"
COPY --chown=app:app . .
RUN python samples/gerar_contrato_exemplo.py && python -m pytest -q
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-server-header"]
