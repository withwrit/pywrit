// Fixture: factory-pattern generated resource (older twilio-node style)
// where write methods hang off an object, and a request pipeline that takes
// the HTTP method as a leading string argument. Reads must not be flagged.
class Pipeline {
  request(method: string, opts: any): Promise<any> {
    return Promise.resolve(opts);
  }
}

export function MessageListInstance(version: Pipeline) {
  const instance: any = {};

  instance.create = function create() {
    return version.request("post", { uri: "/Messages.json" }); // expect: resource-write
  };

  instance.remove = function remove() {
    return version.request("delete", { uri: "/Messages.json" }); // expect: resource-write
  };

  instance.fetch = function fetch() {
    return version.request("get", { uri: "/Messages.json" });
  };

  return instance;
}
