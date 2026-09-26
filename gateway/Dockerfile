FROM public.ecr.aws/nginx/nginx-unprivileged:alpine

# Rendered to /etc/nginx/conf.d/default.conf at startup by the image's entrypoint,
# substituting only environment variables that are actually set.
COPY templates /etc/nginx/templates
