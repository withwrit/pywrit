// Fixture: generated REST resource clients (twilio-style). Resource methods
// named create/update/patch/remove (and ...WithHttpInfo variants) build
// request options with an explicit write HTTP method and route them through
// the version request pipeline. The pipeline may route a write through a
// read-named method (Version.fetch for DELETE-with-body); the literal method
// decides, so only enclosing write methods with write literals are findings
// and method: "get" is never flagged.
class Version {
  request(opts: any): Promise<any> {
    return Promise.resolve(opts);
  }
  create(opts: any): Promise<any> {
    return this.request(opts);
  }
  update(opts: any): Promise<any> {
    return this.request(opts);
  }
  patch(opts: any): Promise<any> {
    return this.request(opts);
  }
  remove(opts: any): Promise<any> {
    return this.request(opts);
  }
  fetch(opts: any): Promise<any> {
    return this.request(opts);
  }
  page(opts: any): Promise<any> {
    return this.request(opts);
  }
  updateWithResponseInfo(opts: any): Promise<any> {
    return this.request(opts);
  }
  removeWithResponseInfo(opts: any): Promise<any> {
    return this.request(opts);
  }
}

export class AccountContext {
  version: Version;
  _uri: string;

  constructor(version: Version, uri: string) {
    this.version = version;
    this._uri = uri;
  }

  fetch() {
    return this.version.fetch({ uri: this._uri, method: "get" });
  }

  update() {
    return this.version.update({ uri: this._uri, method: "post" }); // expect: resource-write
  }

  updateWithHttpInfo() {
    return this.version.updateWithResponseInfo({ uri: this._uri, method: "post" }); // expect: resource-write
  }

  remove() {
    return this.version.fetch({ uri: this._uri, method: "delete" }); // expect: resource-write
  }

  removeWithHttpInfo() {
    return this.version.removeWithResponseInfo({ uri: this._uri, method: "delete" }); // expect: resource-write
  }

  patch() {
    return this.version.patch({ uri: this._uri, method: "patch" }); // expect: resource-write
  }

  list() {
    return this.version.page({ uri: this._uri, method: "get" });
  }
}
