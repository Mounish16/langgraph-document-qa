FROM python:3.11-slim

WORKDIR /app

# pandoc (DOCX) + WeasyPrint (PDF) let the app export answers for download.
# WeasyPrint renders PDF from HTML, so no LaTeX toolchain is needed. Its runtime
# libraries (Pango / HarfBuzz / fontconfig + a base font) are installed here; the
# WeasyPrint Python package itself comes from requirements.txt.
RUN apt-get update && apt-get install -y --no-install-recommends \
      pandoc \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libfontconfig1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# System deps kept minimal; faiss-cpu ships wheels.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY frontend/ ./frontend/

# data/, outputs/, faiss_index/ are mounted at runtime via docker-compose.
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
