// backend url, set VITE_API_BASE_URL in frontend/.env to change it
export const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

let token = null;
let onUnauthorized = () => {};

export function setToken(value) {
  token = value;
}

// auth context registers this, so a 401 anywhere logs the user out
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function toError(res) {
  let code = "error";
  let message = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    // backend always sends {"error": {"code", "message"}}
    code = body.error?.code ?? code;
    message = body.error?.message ?? message;
  } catch {
    // not json, keep the default message
  }
  return new ApiError(res.status, code, message);
}

function authHeaders() {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function handle401(res, path) {
  // a wrong password on /auth/login is also 401, that one shouldn't log anyone out
  if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
}

export async function api(path, { method = "GET", body, params } = {}) {
  const url = new URL(API_URL + path);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === "") continue;
      // arrays become repeated params: ?status=A&status=B
      for (const v of [].concat(value)) url.searchParams.append(key, v);
    }
  }
  const res = await fetch(url, {
    method,
    headers: { ...authHeaders(), ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    handle401(res, path);
    throw await toError(res);
  }
  return res.status === 204 ? null : res.json();
}

// fetch can't report upload progress, XMLHttpRequest can
export function uploadFile(ticketId, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/complaints/${ticketId}/attachments`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      let body = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        // ignore
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body);
      else {
        if (xhr.status === 401) onUnauthorized();
        reject(new ApiError(xhr.status, body?.error?.code ?? "error", body?.error?.message ?? "Upload failed"));
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "network", "Network error, is the backend running?"));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

// files need the token too, so <img src> can't load them directly.
// we fetch the bytes and turn them into a local blob: url
export async function fetchFileUrl(attachmentId) {
  const res = await fetch(`${API_URL}/attachments/${attachmentId}`, { headers: authHeaders() });
  if (!res.ok) {
    handle401(res, "/attachments");
    throw await toError(res);
  }
  return URL.createObjectURL(await res.blob());
}
