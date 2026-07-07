/* ============================================================
   useProfile.test.js — Tests del hook de perfil de usuario.
   Verifica estados iniciales y setters.
   ============================================================ */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useProfile from '../useProfile';

const mockFetchData = () => {};

describe('useProfile', () => {
  it('inicia con perfil por defecto', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    expect(result.current.profile.name).toBe("Andrés");
    expect(result.current.profile.email).toBe("andres@finsys.os");
    expect(result.current.profile.role).toBe("Administrador Contable");
    expect(result.current.profile.avatar_style).toBe("pixel-grid");
  });

  it('no está en modo edición inicialmente', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    expect(result.current.isEditingProfile).toBe(false);
  });

  it('permite actualizar nombre de edición', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    act(() => result.current.setEditProfileName("Carlos"));
    expect(result.current.editProfileName).toBe("Carlos");
  });

  it('permite cambiar avatar style', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    act(() => result.current.setEditProfileAvatar("retro-block"));
    expect(result.current.editProfileAvatar).toBe("retro-block");
  });

  it('toggle modo edición', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    act(() => result.current.setIsEditingProfile(true));
    expect(result.current.isEditingProfile).toBe(true);
    act(() => result.current.setIsEditingProfile(false));
    expect(result.current.isEditingProfile).toBe(false);
  });

  it('setProfile reemplaza perfil completo', () => {
    const { result } = renderHook(() => useProfile({ fetchData: mockFetchData }));
    const newProfile = {
      name: "Test User",
      email: "test@finsys.os",
      role: "Viewer",
      avatar_style: "minimal"
    };
    act(() => result.current.setProfile(newProfile));
    expect(result.current.profile).toEqual(newProfile);
  });
});
