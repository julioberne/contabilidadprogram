/* ============================================================
   ContextPanelAdapter.jsx — Adapter del Panel Contextual (7 tabs)
   Monta el ContextPanel de v1 VERBATIM (import transitorio)
   armando los objetos de props (tercero/taxes/cartera/assets/
   tagState/profileEdit) desde el draft context + empresa,
   con el wiring EXACTO de App.jsx:613-661 — incluidos los
   setters no-op de taxes (type/customRate) que v1 pasa así.
   ============================================================ */
import { useEffect } from 'react';
import ContextPanel from '../../components/ContextPanel.jsx';
import useProfile from '../../hooks/useProfile.js';
import { useEmpresa } from '../engine/EmpresaProvider.jsx';
import { useTransactionDraft } from '../engine/TransactionDraftProvider.jsx';

export default function ContextPanelAdapter({ activeTab, setActiveTab }) {
  const empresa = useEmpresa();
  const draft = useTransactionDraft();

  // Perfil: hook v1 + sincronización desde dashboard-data
  // (en v1 fetchData hacía setProfile + setEditProfile*; App.jsx:196-201)
  const perfil = useProfile({ fetchData: empresa.fetchAll });
  const { setProfile, setEditProfileName, setEditProfileEmail, setEditProfileRole, setEditProfileAvatar } = perfil;
  useEffect(() => {
    if (empresa.profile && empresa.profile.name) {
      setProfile(empresa.profile);
      setEditProfileName(empresa.profile.name);
      setEditProfileEmail(empresa.profile.email);
      setEditProfileRole(empresa.profile.role);
      setEditProfileAvatar(empresa.profile.avatar_style);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresa.profile]);

  return (
    <ContextPanel
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      tercero={{
        name: draft.thirdPartyName, setName: draft.setThirdPartyName,
        idType: draft.thirdPartyType, setIdType: draft.setThirdPartyType,
        idNumber: draft.thirdPartyNumber, setIdNumber: draft.setThirdPartyNumber,
        email: draft.thirdPartyEmail, setEmail: draft.setThirdPartyEmail,
        phone: draft.thirdPartyPhone, setPhone: draft.setThirdPartyPhone,
        address: draft.thirdPartyWebsite, setAddress: draft.setThirdPartyWebsite,
      }}
      taxes={{
        enabled: draft.applyIva, setEnabled: draft.setApplyIva,
        type: 'IVA_19', setType: () => {},
        customRate: '', setCustomRate: () => {},
      }}
      cartera={{
        enabled: draft.cxcCxpEnabled, setEnabled: draft.setCxcCxpEnabled,
        type: draft.cxcCxpType, setType: draft.setCxcCxpType,
        dueDate: draft.cxcCxpDueDate, setDueDate: draft.setCxcCxpDueDate,
        term: draft.cxcCxpTerm, setTerm: draft.setCxcCxpTerm,
        partialValue: draft.cxcCxpValue, setPartialValue: draft.setCxcCxpValue,
        totalAmount: draft.amount,
      }}
      assets={{
        enabled: draft.assetEnabled, setEnabled: draft.setAssetEnabled,
        name: draft.assetName, setName: draft.setAssetName,
        value: draft.assetValue, setValue: draft.setAssetValue,
        tag: draft.assetTag, setTag: draft.setAssetTag,
      }}
      tagState={{
        selected: draft.selectedTags, setSelected: draft.setSelectedTags,
        search: draft.tagSearch, setSearch: draft.setTagSearch,
      }}
      allThirdParties={empresa.allThirdParties}
      setAllThirdParties={empresa.setAllThirdParties}
      activePortfolio={empresa.activePortfolio}
      activeCompany={empresa.activeCompany}
      onCompanyUpdated={(updated) => empresa.setActiveCompany(updated)}
      accounts={empresa.accounts}
      profile={perfil.profile}
      profileEdit={{
        isEditing: perfil.isEditingProfile, setIsEditing: perfil.setIsEditingProfile,
        name: perfil.editProfileName, setName: perfil.setEditProfileName,
        email: perfil.editProfileEmail, setEmail: perfil.setEditProfileEmail,
        role: perfil.editProfileRole, setRole: perfil.setEditProfileRole,
        handleSave: perfil.handleUpdateProfile,
      }}
    />
  );
}
