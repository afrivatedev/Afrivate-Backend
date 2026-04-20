# Profile creation and role assignment are handled by profiles/signals.py.
# That handler uses QuerySet.update() to avoid re-triggering post_save.
# Do not add a second post_save handler for CustomUser here.
