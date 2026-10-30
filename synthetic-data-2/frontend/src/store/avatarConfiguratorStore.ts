import { create } from "zustand";
import { MeshStandardMaterial } from "three";
import { randInt } from "three/src/math/MathUtils.js";

export const PHOTO_POSES = {
  Idle: "Idle",
  Chill: "Chill",
  Cool: "Cool",
  Punch: "Punch",
  Ninja: "Ninja",
  King: "King",
  Busy: "Busy",
};

export const UI_MODES = {
  PHOTO: "photo",
  CUSTOMIZE: "customize",
};

// Persona categories mapped to avatar customization
const PERSONA_CATEGORIES = [
  {
    id: "body",
    name: "Body",
    position: 0,
    removable: false,
    colorPalette: {
      colors: ["#f5c6a5", "#e8b896", "#d4a574", "#c19552", "#8b6914"]
    },
    assets: [
      { id: "NakedFullBody", name: "Base Body", thumbnail: "body.jpg" }
    ]
  },
  {
    id: "basicInfo",
    name: "Basic Info",
    position: 1,
    removable: false,
    colorPalette: {
      colors: ["#f5c6a5", "#e8b896", "#d4a574", "#c19552", "#8b6914"]
    },
    assets: [
      { id: "Head.001", name: "Head Style 1", thumbnail: "face1.jpg" },
      { id: "Head.002", name: "Head Style 2", thumbnail: "face2.jpg" },
      { id: "Head.003", name: "Head Style 3", thumbnail: "face3.jpg" },
      { id: "Head.004", name: "Head Style 4", thumbnail: "face4.jpg" }
    ]
  },
  {
    id: "top",
    name: "Top",
    position: 2,
    removable: true,
    colorPalette: {
      colors: ["#2563eb", "#1d4ed8", "#1e40af", "#1e3a8a", "#172554"]
    },
    assets: [
      { id: "Top.001", name: "Shirt 1", thumbnail: "top1.jpg" },
      { id: "Top.002", name: "Shirt 2", thumbnail: "top2.jpg" },
      { id: "Top.003", name: "Shirt 3", thumbnail: "top3.jpg" }
    ]
  },
  {
    id: "bottom",
    name: "Bottom",
    position: 3,
    removable: true,
    colorPalette: {
      colors: ["#1f2937", "#111827", "#374151"]
    },
    assets: [
      { id: "Bottom.001", name: "Pants 1", thumbnail: "bottom1.jpg" },
      { id: "Bottom.002", name: "Pants 2", thumbnail: "bottom2.jpg" },
      { id: "Bottom.003", name: "Pants 3", thumbnail: "bottom3.jpg" }
    ]
  },
  {
    id: "footwear",
    name: "Footwear",
    position: 4,
    removable: true,
    colorPalette: {
      colors: ["#6b7280", "#374151", "#111827"]
    },
    assets: [
      { id: "Shoes.001", name: "Sneakers 1", thumbnail: "shoes1.jpg" },
      { id: "Shoes.002", name: "Sneakers 2", thumbnail: "shoes2.jpg" },
      { id: "Shoes.003", name: "Shoes 3", thumbnail: "shoes3.jpg" }
    ]
  },
  {
    id: "personality",
    name: "Personality",
    position: 5,
    removable: true,
    colorPalette: {
      colors: ["#dc2626", "#b91c1c", "#991b1b", "#7f1d1d", "#450a0a"]
    },
    assets: [
      { id: "Eyes.001", name: "Confident", thumbnail: "expr1.jpg" },
      { id: "Eyes.002", name: "Friendly", thumbnail: "expr2.jpg" },
      { id: "Eyes.003", name: "Serious", thumbnail: "expr3.jpg" }
    ]
  },
  {
    id: "behavioral",
    name: "Behavioral",
    position: 6,
    removable: true,
    colorPalette: {
      colors: ["#059669", "#047857", "#065f46", "#064e3b", "#022c22"]
    },
    assets: [
      { id: "Hair.001", name: "Active", thumbnail: "pose1.jpg" },
      { id: "Hair.002", name: "Relaxed", thumbnail: "pose2.jpg" },
      { id: "Hair.003", name: "Dynamic", thumbnail: "pose3.jpg" }
    ]
  },
  {
    id: "mediaConsumption",
    name: "Media",
    position: 7,
    removable: true,
    colorPalette: {
      colors: ["#7c3aed", "#6d28d9", "#5b21b6", "#4c1d95", "#2d1b69"]
    },
    assets: [
      { id: "Glasses.001", name: "Tech Savvy", thumbnail: "acc1.jpg" },
      { id: "Glasses.002", name: "Traditional", thumbnail: "acc2.jpg" },
      { id: "Glasses.003", name: "Trendy", thumbnail: "acc3.jpg" }
    ]
  },
  {
    id: "goals",
    name: "Goals",
    position: 8,
    removable: true,
    colorPalette: {
      colors: ["#ea580c", "#dc2626", "#c2410c", "#9a3412", "#7c2d12"]
    },
    assets: [
      { id: "Top.001", name: "Ambitious", thumbnail: "bg1.jpg" },
      { id: "Top.002", name: "Balanced", thumbnail: "bg2.jpg" },
      { id: "Top.003", name: "Creative", thumbnail: "bg3.jpg" }
    ]
  },
  {
    id: "context",
    name: "Context",
    position: 9,
    removable: true,
    colorPalette: {
      colors: ["#0891b2", "#0e7490", "#155e75", "#164e63", "#083344"]
    },
    assets: [
      { id: "Hat.001", name: "Corporate", thumbnail: "env1.jpg" },
      { id: "Hat.002", name: "Startup", thumbnail: "env2.jpg" },
      { id: "Hat.003", name: "Retail", thumbnail: "env3.jpg" }
    ]
  }
];

interface AvatarConfiguratorState {
  loading: boolean;
  mode: string;
  pose: string;
  categories: any[];
  currentCategory: any;
  assets: any[];
  lockedGroups: Record<string, any>;
  skin: MeshStandardMaterial;
  customization: Record<string, any>;
  download: () => void;
  screenshot: () => void;
  setMode: (mode: string) => void;
  setPose: (pose: string) => void;
  updateColor: (color: string) => void;
  updateSkin: (color: string) => void;
  fetchCategories: () => Promise<void>;
  setCurrentCategory: (category: any) => void;
  changeAsset: (category: string, asset: any) => void;
  randomize: () => void;
  applyLockedAssets: () => void;
  setDownload: (download: () => void) => void;
  setScreenshot: (screenshot: () => void) => void;
}

export const useAvatarConfiguratorStore = create<AvatarConfiguratorState>((set, get) => ({
  loading: true,
  mode: UI_MODES.CUSTOMIZE,
  setMode: (mode: string) => {
    set({ mode });
    if (mode === UI_MODES.CUSTOMIZE) {
      set({ pose: PHOTO_POSES.Idle });
    }
  },
  pose: PHOTO_POSES.Idle,
  setPose: (pose: string) => set({ pose }),
  categories: [],
  currentCategory: null,
  assets: [],
  lockedGroups: {},
  skin: new MeshStandardMaterial({ color: 0xf5c6a5, roughness: 1 }),
  customization: {},
  download: () => {},
  setDownload: (download: () => void) => set({ download }),
  screenshot: () => {},
  setScreenshot: (screenshot: () => void) => set({ screenshot }),
  updateColor: (color: string) => {
    set((state) => ({
      customization: {
        ...state.customization,
        [state.currentCategory.name]: {
          ...state.customization[state.currentCategory.name],
          color,
        },
      },
    }));
    if (get().currentCategory.name === "Body" || get().currentCategory.name === "Basic Info") {
      get().updateSkin(color);
    }
  },
  updateSkin: (color: string) => {
    get().skin.color.set(color);
  },
  fetchCategories: async () => {
    set({ loading: true });
    // Simulate async loading with mock data
    await new Promise(resolve => setTimeout(resolve, 500));
    const categories = PERSONA_CATEGORIES;
    set({ categories, currentCategory: categories[0] || null, loading: false });
    get().applyLockedAssets();
  },
  setCurrentCategory: (category: any) => set({ currentCategory: category }),
  changeAsset: (category: string, asset: any) => {
    set((state) => ({
      customization: {
        ...state.customization,
        [category]: {
          ...state.customization[category],
          asset,
        },
      },
    }));
    get().applyLockedAssets();
  },
  randomize: () => {
    const customization: Record<string, any> = {};
    get().categories.forEach((category) => {
      let randomAsset = category.assets[randInt(0, category.assets.length - 1)];
      if (category.removable) {
        if (randInt(0, category.assets.length - 1) === 0) {
          randomAsset = null;
        }
      }
      const randomColor =
        category.colorPalette?.colors?.[randInt(0, category.colorPalette.colors.length - 1)];
      customization[category.name] = {
        asset: randomAsset,
        color: randomColor,
      };
      if (category.name === "Body" || category.name === "Basic Info") {
        get().updateSkin(randomColor);
      }
    });
    set({ customization });
    get().applyLockedAssets();
  },
  applyLockedAssets: () => {
    // Simplified for mock data - select sensible defaults for a basic human
    const { categories, customization } = get();
    const newCustomization = { ...customization };
    const defaultOn = new Set(["Body", "Basic Info", "Top", "Bottom", "Personality", "Behavioral", "Footwear"]);

    categories.forEach((category) => {
      if (!newCustomization[category.name]) {
        newCustomization[category.name] = {
          asset: defaultOn.has(category.name) ? (category.assets[0] || null) : null,
          color: category.colorPalette?.colors?.[0] || "#ffffff",
        };
      } else if (newCustomization[category.name].asset === undefined) {
        // Ensure asset key exists and apply default if needed
        newCustomization[category.name].asset = defaultOn.has(category.name) ? (category.assets[0] || null) : null;
      }
    });

    // Set skin color based on Body category default
    if (newCustomization["Body"]?.color) {
      get().updateSkin(newCustomization["Body"].color);
    }

    set({ customization: newCustomization });
  },
}));

// Initialize the store
useAvatarConfiguratorStore.getState().fetchCategories();