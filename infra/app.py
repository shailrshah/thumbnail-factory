import os

import aws_cdk as cdk

from thumbnail_factory_infra.stack import ThumbnailFactoryStack

app = cdk.App()
ThumbnailFactoryStack(
    app,
    "ThumbnailFactory",
    # The project may only create resources in its selected Region (D10).
    env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-east-2"),
)
cdk.Tags.of(app).add("project", "thumbnail-factory")
app.synth()
