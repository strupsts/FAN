from __future__ import annotations

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.adapters.inbound.api.dependencies import (
    get_container,
    get_current_user_id,
)
from app.adapters.inbound.api.routes.user_schemas import (
    CurrentUserProfileResponse,
    SetUserPreferencesRequest,
    UserPreferencesResponse,
    preferences_to_response,
    profile_to_response,
)
from app.application import (
    CurrentUserNotFoundError,
    SetUserPreferencesCommand,
)
from app.infrastructure import AppContainer


router = APIRouter(
    prefix="/api/users",
    tags=["users"],
)


@router.get(
    "/me",
    response_model=CurrentUserProfileResponse,
)
def get_current_user_profile(
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> CurrentUserProfileResponse:
    try:
        profile = (
            container
            .get_current_user_profile_use_case
            .execute(user_id)
        )
    except CurrentUserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user was not found.",
        ) from error

    return profile_to_response(profile)


@router.put(
    "/me/preferences",
    response_model=UserPreferencesResponse,
)
def set_current_user_preferences(
    request: SetUserPreferencesRequest,
    container: AppContainer = Depends(get_container),
    user_id: UUID = Depends(get_current_user_id),
) -> UserPreferencesResponse:
    command = SetUserPreferencesCommand(
        user_id=user_id,
        interface_language=request.interface_language,
        formatting_locale=request.formatting_locale,
        home_country=request.home_country,
        default_receipt_currency=(
            request.default_receipt_currency
        ),
        reporting_currency=request.reporting_currency,
        time_zone=request.time_zone,
        onboarding_completed=(
            request.onboarding_completed
        ),
    )

    try:
        preferences = (
            container
            .set_user_preferences_use_case
            .execute(command)
        )
    except CurrentUserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current user was not found.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="User preferences are invalid.",
        ) from error

    return preferences_to_response(preferences)
