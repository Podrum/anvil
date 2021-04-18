from region import region

reg: object = region("./r.0.0.mca")
reg.load_chunks()
reg.save_chunks()
