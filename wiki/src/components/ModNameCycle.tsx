import {useEffect, useState, type ReactNode} from 'react';
import styles from './ModNameCycle.module.css';

const MOD_NAMES = [
  'MyTacticalVest',
  'BananaLauncher',
  'MyMedicalKit',
  'AggressiveChicken9000',
  'MyArmorMod',
  'BulletproofPajamas',
  'MyTraderConfig',
  'CursedCowboy',
  'MyLootRework',
  'HazmatHotdogStand',
  'MyClothingPack',
  'KarenSimulator',
  'MyHUDOverhaul',
  'BabyShark_Hostiles',
  'MyServerTools',
  'LegallyDistinctRifle',
  'MyVehiclePack',
  'ParkourGoatPack',
  'MyMapAddons',
  'ZombieKaraoke',
  'MyWeaponSkin',
  'ExistentialDreadHUD',
  'MyBaseBuildingExt',
  'TacticalRubberDuck',
];

export default function ModNameCycle(): ReactNode {
  const [idx, setIdx] = useState(0);
  const [text, setText] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = MOD_NAMES[idx % MOD_NAMES.length];
    let timer: ReturnType<typeof setTimeout>;
    if (!deleting && text === current) {
      timer = setTimeout(() => setDeleting(true), 1800);
    } else if (deleting && text === '') {
      setDeleting(false);
      setIdx((i) => i + 1);
    } else if (deleting) {
      timer = setTimeout(() => setText(text.slice(0, -1)), 32);
    } else {
      timer = setTimeout(() => setText(current.slice(0, text.length + 1)), 70);
    }
    return () => clearTimeout(timer);
  }, [text, deleting, idx]);

  return (
    <>
      {text}
      <span className={styles.cursor}>|</span>
    </>
  );
}
