FROM python:3

# Set working directory
WORKDIR /project

# Copy dependency files
COPY pyproject.toml .
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy the rest of the application
COPY src/ ./src/

# Set proper permissions
RUN chown -R appuser:appuser /project

# Expose the port the app runs on
EXPOSE 8000

WORKDIR /project/src

# Switch to non-root user
USER appuser

# Command to run the application
CMD ["python", "run.py"]