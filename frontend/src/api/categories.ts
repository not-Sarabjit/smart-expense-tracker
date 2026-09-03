import apiClient from "./client";
import type {
  Category,
  CategoryCreatePayload,
  CategoryUpdatePayload,
} from "../types";

export function getCategories(): Promise<Category[]> {
  return apiClient.get<Category[]>("/categories/").then((res) => res.data);
}

export function createCategory(
  payload: CategoryCreatePayload
): Promise<Category> {
  return apiClient
    .post<Category>("/categories/create_category", payload)
    .then((res) => res.data);
}

export function updateCategory(
  id: number,
  payload: CategoryUpdatePayload
): Promise<Category> {
  return apiClient
    .put<Category>(`/categories/${id}`, payload)
    .then((res) => res.data);
}

export function deleteCategory(id: number): Promise<void> {
  return apiClient.delete(`/categories/${id}`).then(() => undefined);
}
