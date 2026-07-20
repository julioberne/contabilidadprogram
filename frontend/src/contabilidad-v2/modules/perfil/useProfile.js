/* ============================================================
   useProfile.js — Perfil de usuario (lectura + edición).
   Extraído de App.jsx (estados L43-53, función L600-623)
   ============================================================ */
import { useState } from 'react';
import { API } from '../../../config';

const API_BASE_URL = API;

export default function useProfile({ fetchData }) {
  const [profile, setProfile] = useState({
    name: "Andrés",
    email: "andres@finsys.os",
    role: "Administrador Contable",
    avatar_style: "pixel-grid"
  });
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editProfileName, setEditProfileName] = useState("");
  const [editProfileEmail, setEditProfileEmail] = useState("");
  const [editProfileRole, setEditProfileRole] = useState("");
  const [editProfileAvatar, setEditProfileAvatar] = useState("pixel-grid");

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE_URL}/profile`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editProfileName,
          email: editProfileEmail,
          role: editProfileRole,
          avatar_style: editProfileAvatar
        })
      });
      if (res.ok) {
        setIsEditingProfile(false);
        fetchData();
      } else {
        alert("❌ Error al actualizar el perfil.");
      }
    } catch (error) {
      alert("❌ Error al conectar con el servidor.");
    }
  };

  return {
    profile, setProfile,
    isEditingProfile, setIsEditingProfile,
    editProfileName, setEditProfileName,
    editProfileEmail, setEditProfileEmail,
    editProfileRole, setEditProfileRole,
    editProfileAvatar, setEditProfileAvatar,
    handleUpdateProfile,
  };
}
