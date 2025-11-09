from typing import Any, Dict, Optional

from spectacles.client import LOOKML_VALIDATION_TIMEOUT, LookerClient
from spectacles.exceptions import LookMLError
from spectacles.logger import GLOBAL_LOGGER as logger

# Define constants for severity levels
SUCCESS = 0
INFO = 10
WARNING = 20
ERROR = 30
FATAL = 40

NAME_TO_LEVEL = {
    "success": SUCCESS,
    "info": INFO,
    "warning": WARNING,
    "error": ERROR,
    "fatal": FATAL,
}


class LookMLValidator:
    """Runs LookML validator for a given project.

    Args:
        client: Looker API client.
        project: Name of the LookML project to validate.

    """

    def __init__(self, client: LookerClient):
        self.client = client

    async def validate(
        self,
        project: str,
        severity: str = "warning",
        timeout: int = LOOKML_VALIDATION_TIMEOUT,
    ) -> Dict[str, Any]:
        severity_level: int = NAME_TO_LEVEL[severity]
        # Skip cache check - it can hang when switching branches or after reset
        # Go directly to POST validation to ensure we get fresh results
        logger.debug(f"Validating LookML for project '{project}' (skipping cache)")
        validation_results = await self.client.lookml_validation(project, timeout)
        errors = []
        lookml_url: Optional[str] = None
        for error in validation_results["errors"]:
            if error["file_path"]:
                lookml_url = (
                    self.client.base_url
                    + "/projects/"
                    + project
                    + "/files/"
                    + "/".join(error["file_path"].split("/")[1:])
                )
                if error["line_number"]:
                    lookml_url += "?line=" + str(error["line_number"])

            lookml_error = LookMLError(
                model=error["model_id"],
                explore=error["explore"],
                field_name=error["field_name"],
                message=error["message"],
                severity=error["severity"],
                lookml_url=lookml_url,
                line_number=error["line_number"],
                file_path=error["file_path"],
            )
            errors.append(lookml_error)

        if any(NAME_TO_LEVEL[e.metadata["severity"]] >= severity_level for e in errors):
            status = "failed"
        else:
            status = "passed"

        result = {
            "validator": "lookml",
            "errors": [error.to_dict() for error in errors],
            "status": status,
        }
        return result
