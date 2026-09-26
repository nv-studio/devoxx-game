using Unity.Cinemachine;
using UnityEngine;

namespace DevoxxGame.Players
{
    /// <summary>
    /// Owns this player's camera. Living inside the PlayerRig prefab is what lets every reference
    /// here be an in-prefab reference instead of a scene hookup or a Camera.main lookup.
    /// </summary>
    public class PlayerCameraRig : MonoBehaviour
    {
        [field: SerializeField] public CinemachineCamera VirtualCamera { get; private set; }

        /// <summary>The live camera transform, used to resolve input into camera-relative motion.</summary>
        [field: SerializeField] public Transform YawReference { get; private set; }

        public void SetTarget(Transform target)
        {
            if (!VirtualCamera)
                return;

            VirtualCamera.Target.TrackingTarget = target;
            VirtualCamera.Target.LookAtTarget = target;
        }
    }
}
