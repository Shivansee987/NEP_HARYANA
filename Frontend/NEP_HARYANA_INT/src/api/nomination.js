import { request } from "./auth";

export function fetchNominations() {
  return request("/nominations/");
}

export function fetchMySubmissions() {
  return request("/nominations/my-submissions/");
}

export function fetchNominationDetails(id) {
  return request(`/nominations/${id}/`);
}

export function saveNomination(id, payload) {
  return request(`/nominations/${id}/save/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitNomination(id, payload) {
  return request(`/nominations/${id}/submit/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchCloudinaryConfig() {
  return request("/nominations/config/");
}

export function fetchNominationConfig() {
  return request("/nominations/config/");
}

export async function uploadEvidenceToCloudinary(file) {
  const formData = new FormData();
  formData.append("file", file);
  return request("/nominations/upload/", {
    method: "POST",
    body: formData,
  });
}
