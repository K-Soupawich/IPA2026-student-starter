from app.core import process_request_file
def validate_webex_envelope(
    mentioned_people,
    attachment_path,
    bot_person_id,
):
    """
    Validate the target bot's actual mention and YAML attachment.
    Return an error response, or None when the envelope is valid.
    """
    # 1.
    if (not isinstance(bot_person_id, str) or not bot_person_id # bot_person_id must be a non-empty string
        or not isinstance(mentioned_people, list) # mentioned_people must be a list
        or bot_person_id not in mentioned_people # must containing bot_person_id
    ):
        return {"status": "error", "result": "missing_bot_mention"}
    
    # 2. attachment_path is None
    if attachment_path is None:
        return {"status": "error", "result": "no_yaml"}
    
    # 3. return None if pass
    return None

def handle_webex_request(
    mentioned_people,
    attachment_path,
    bot_person_id,
):
    """
    Validate the envelope, then validate the attached YAML request.
    Return a response dictionary. Do not dispatch to a router.
    """
    error = validate_webex_envelope(
        mentioned_people,
        attachment_path,
        bot_person_id
    )
    
    if error is not None:
        return error
    return process_request_file(attachment_path)
