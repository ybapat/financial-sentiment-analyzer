# --- Stage 1: Base Image ---
# We start with an official Python image. Using 'slim' makes it smaller.
FROM python:3.9-slim

# --- Stage 2: Set up the Environment ---
# Set the working directory inside the container. All subsequent commands
# will run from this path.
WORKDIR /app

# --- Stage 3: Copy Files and Install Dependencies ---
# First, copy only the requirements file. This is a key optimization.
# Docker caches layers, so it will only re-run this step if requirements.txt changes.
COPY requirements.txt .

# Install the Python libraries specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Now, copy the rest of your application code and data into the container.
COPY . .

# --- Stage 4: Train the Model ---
# Run the sentiment analyzer script to generate the .pkl model files.
# This happens *during the build*, so the files are part of the final image.
RUN python sentiment_analysis.py

# --- Stage 5: Expose Port and Run the Application ---
# Tell Docker that the container will listen on port 5001.
EXPOSE 5001

# The command to run when the container starts. This executes your Flask app.
# We use gunicorn, a production-ready web server for Python.
RUN pip install gunicorn

# Now, set the command to run the app with gunicorn and a longer timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "120", "app:app"]