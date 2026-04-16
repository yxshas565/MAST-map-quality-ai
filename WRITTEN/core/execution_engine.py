class ExecutionEngine:
    def run(self, code: str) -> dict:
        import subprocess, tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            path = f.name

        try:
            result = subprocess.run(
                ["python", path],
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }

        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }